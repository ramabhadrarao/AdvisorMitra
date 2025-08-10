# services/live_progress_service.py
# ENHANCED - Added form state restoration capability

import redis
import json
from flask import current_app
from flask_socketio import emit, join_room, leave_room
from flask_login import current_user
import logging
from datetime import datetime

class LiveProgressService:
    def __init__(self):
        self.redis_client = None
        self.logger = logging.getLogger(__name__)
        self._initialized = False
    
    def _init_redis(self):
        """Initialize Redis connection with proper Flask context"""
        if self._initialized:
            return
            
        try:
            if current_app:
                redis_url = current_app.config.get('REDIS_URL', 'redis://localhost:6379/0')
                self.redis_client = redis.from_url(redis_url)
                self.redis_client.ping()
                print("✅ Redis connected successfully")
                self._initialized = True
        except Exception as e:
            self.logger.warning(f"Redis connection failed: {e}. Live progress will not work.")
            print(f"❌ Redis connection failed: {e}")
            self.redis_client = None
    
    def _ensure_redis(self):
        """Ensure Redis is initialized before use"""
        if not self._initialized:
            self._init_redis()
        return self.redis_client is not None
    
    def get_progress_key(self, token):
        """Generate Redis key for form progress"""
        return f"form_progress:{token}"
    
    def get_agent_forms_key(self, agent_id):
        """Generate Redis key for agent's active forms list"""
        return f"agent_forms:{agent_id}"
    
    def get_form_progress(self, token):
        """Get current form progress - ENHANCED with better error handling"""
        if not self._ensure_redis():
            print("❌ Redis not available for getting progress")
            return None
        
        try:
            progress_key = self.get_progress_key(token)
            progress_data = self.redis_client.get(progress_key)
            
            if progress_data:
                data = json.loads(progress_data)
                print(f"📊 Retrieved progress for {token}: {data.get('percentage', 0):.1f}%")
                return data
            else:
                print(f"📭 No progress data found for token: {token}")
                
        except Exception as e:
            self.logger.error(f"Error getting form progress: {e}")
            print(f"❌ Error getting progress: {e}")
        
        return None
    
    def update_form_progress(self, token, field_name, field_value, total_fields=12):
        """Update form progress in Redis and track in agent's active forms"""
        if not self._ensure_redis():
            print("❌ Redis not available for progress update")
            return None
        
        try:
            progress_key = self.get_progress_key(token)
            
            # Get current progress
            current_progress = self.redis_client.get(progress_key)
            if current_progress:
                progress_data = json.loads(current_progress)
            else:
                progress_data = {
                    'completed_fields': {},
                    'start_time': self._get_current_timestamp(),
                    'last_update': None,
                    'customer_info': {},
                    'percentage': 0,
                    'status': 'active',
                    'token': token,
                    'agent_id': None
                }
            
            # Handle special events
            if field_name == 'form_started':
                progress_data['status'] = 'active'
                progress_data['last_update'] = self._get_current_timestamp()
                self.redis_client.setex(progress_key, 7200, json.dumps(progress_data))
                
                if progress_data.get('agent_id'):
                    self._update_agent_active_forms(progress_data['agent_id'], token, progress_data)
                
                print(f"✅ Form session started for token: {token}")
                return progress_data
            
            elif field_name == 'form_restored':
                progress_data['status'] = 'active'
                progress_data['last_update'] = self._get_current_timestamp()
                progress_data['restored'] = True
                progress_data['restored_at'] = self._get_current_timestamp()
                self.redis_client.setex(progress_key, 7200, json.dumps(progress_data))
                
                if progress_data.get('agent_id'):
                    self._update_agent_active_forms(progress_data['agent_id'], token, progress_data)
                
                print(f"🔄 Form data restored for token: {token}")
                return progress_data
            
            elif field_name == 'form_submitted':
                progress_data['status'] = 'completed'
                progress_data['percentage'] = 100
                progress_data['completion_time'] = self._get_current_timestamp()
                progress_data['last_update'] = self._get_current_timestamp()
                self.redis_client.setex(progress_key, 86400, json.dumps(progress_data))
                
                if progress_data.get('agent_id'):
                    self._update_agent_active_forms(progress_data['agent_id'], token, progress_data)
                
                print(f"✅ Form completed for token: {token}")
                return progress_data
            
            # Update field data (only for real form fields)
            progress_data['completed_fields'][field_name] = field_value
            progress_data['last_update'] = self._get_current_timestamp()
            
            # Store basic customer info for agent display
            if field_name == 'name' and field_value:
                progress_data['customer_info']['name'] = field_value
            elif field_name == 'email' and field_value:
                progress_data['customer_info']['email'] = field_value
            elif field_name == 'mobile' and field_value:
                progress_data['customer_info']['mobile'] = field_value
            
            # Calculate progress percentage (only count non-empty fields, excluding special fields)
            actual_fields = {k: v for k, v in progress_data['completed_fields'].items() 
                           if k not in ['form_started', 'form_submitted', 'form_restored'] and v and str(v).strip()}
            completed_count = len(actual_fields)
            progress_data['percentage'] = min(100, (completed_count / total_fields) * 100)
            
            # Update status based on progress
            if completed_count > 0:
                progress_data['status'] = 'active'
            
            # Store in Redis with 2 hour expiry
            self.redis_client.setex(progress_key, 7200, json.dumps(progress_data))
            
            # Update agent's active forms list if agent_id is available
            if progress_data.get('agent_id'):
                self._update_agent_active_forms(progress_data['agent_id'], token, progress_data)
            
            print(f"✅ Progress updated for {token}: {completed_count}/{total_fields} fields ({progress_data['percentage']:.1f}%) - Status: {progress_data['status']}")
            
            return progress_data
            
        except Exception as e:
            self.logger.error(f"Error updating form progress: {e}")
            print(f"❌ Error updating progress: {e}")
            return None
    
    def _update_agent_active_forms(self, agent_id, token, progress_data):
        """Update agent's active forms list in Redis"""
        try:
            agent_forms_key = self.get_agent_forms_key(agent_id)
            
            # Get current active forms for agent
            active_forms_data = self.redis_client.get(agent_forms_key)
            if active_forms_data:
                active_forms = json.loads(active_forms_data)
            else:
                active_forms = {}
            
            # Update or add this form
            active_forms[token] = {
                'token': token,
                'agent_id': agent_id,
                'percentage': progress_data.get('percentage', 0),
                'customer_info': progress_data.get('customer_info', {}),
                'last_update': progress_data.get('last_update'),
                'status': progress_data.get('status', 'active'),
                'completed_fields': progress_data.get('completed_fields', {}),
                'restored': progress_data.get('restored', False),
                'restored_at': progress_data.get('restored_at')
            }
            
            # Clean up very old forms (older than 2 hours)
            current_time = datetime.utcnow()
            forms_to_remove = []
            for form_token, form_data in active_forms.items():
                if form_data.get('last_update'):
                    try:
                        last_update = datetime.fromisoformat(form_data['last_update'])
                        if (current_time - last_update).total_seconds() > 7200:  # 2 hours
                            forms_to_remove.append(form_token)
                    except:
                        pass
            
            for form_token in forms_to_remove:
                active_forms.pop(form_token, None)
            
            # Store updated list with 3 hour expiry
            self.redis_client.setex(agent_forms_key, 10800, json.dumps(active_forms))
            print(f"📊 Updated agent {agent_id} forms list: {len(active_forms)} forms")
            
        except Exception as e:
            self.logger.error(f"Error updating agent active forms: {e}")
    
    def start_form_session(self, token, agent_id):
        """Initialize form progress tracking with agent_id"""
        if not self._ensure_redis():
            print("❌ Redis not available for starting session")
            return
        
        try:
            progress_key = self.get_progress_key(token)
            
            # Check if session already exists
            existing_data = self.redis_client.get(progress_key)
            if existing_data:
                progress_data = json.loads(existing_data)
                # Update agent_id if not set or different
                if not progress_data.get('agent_id') or progress_data.get('agent_id') != str(agent_id):
                    progress_data['agent_id'] = str(agent_id)
                    progress_data['last_update'] = self._get_current_timestamp()
                    self.redis_client.setex(progress_key, 7200, json.dumps(progress_data))
                    # Update agent's active forms list
                    self._update_agent_active_forms(str(agent_id), token, progress_data)
                    print(f"✅ Updated existing session with agent_id: {agent_id}")
                return
            
            # Create new session
            initial_data = {
                'completed_fields': {},
                'start_time': self._get_current_timestamp(),
                'last_update': self._get_current_timestamp(),
                'customer_info': {},
                'percentage': 0,
                'agent_id': str(agent_id),
                'status': 'started',
                'token': token
            }
            
            # Store for 2 hours
            self.redis_client.setex(progress_key, 7200, json.dumps(initial_data))
            
            # Add to agent's active forms
            self._update_agent_active_forms(str(agent_id), token, initial_data)
            
            print(f"✅ Form session started for token: {token} with agent_id: {agent_id}")
            
        except Exception as e:
            self.logger.error(f"Error starting form session: {e}")
            print(f"❌ Error starting session: {e}")
    
    def ensure_agent_id_in_progress(self, token, agent_id):
        """Ensure agent_id is set in existing progress data"""
        if not self._ensure_redis():
            return False
            
        try:
            progress_key = self.get_progress_key(token)
            existing_data = self.redis_client.get(progress_key)
            
            if existing_data:
                progress_data = json.loads(existing_data)
                if not progress_data.get('agent_id') or progress_data.get('agent_id') != str(agent_id):
                    progress_data['agent_id'] = str(agent_id)
                    progress_data['last_update'] = self._get_current_timestamp()
                    self.redis_client.setex(progress_key, 7200, json.dumps(progress_data))
                    # Update agent's active forms list
                    self._update_agent_active_forms(str(agent_id), token, progress_data)
                    print(f"✅ Added agent_id {agent_id} to existing progress for token: {token}")
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error ensuring agent_id: {e}")
            return False
    
    def complete_form_session(self, token):
        """Mark form as completed and update agent's list"""
        if not self._ensure_redis():
            return
        
        try:
            progress_key = self.get_progress_key(token)
            progress_data = self.get_form_progress(token)
            
            if progress_data:
                progress_data['status'] = 'completed'
                progress_data['percentage'] = 100
                progress_data['completion_time'] = self._get_current_timestamp()
                progress_data['last_update'] = self._get_current_timestamp()
                
                # Store for 24 hours after completion
                self.redis_client.setex(progress_key, 86400, json.dumps(progress_data))
                
                # Update agent's active forms list
                if progress_data.get('agent_id'):
                    self._update_agent_active_forms(progress_data['agent_id'], token, progress_data)
                
                print(f"✅ Form session completed for token: {token}")
                
        except Exception as e:
            self.logger.error(f"Error completing form session: {e}")
    
    def get_agent_active_forms(self, agent_id):
        """Get all active forms for an agent from Redis"""
        if not self._ensure_redis():
            return []
        
        try:
            agent_forms_key = self.get_agent_forms_key(agent_id)
            active_forms_data = self.redis_client.get(agent_forms_key)
            
            if active_forms_data:
                active_forms_dict = json.loads(active_forms_data)
                
                # Convert to list and include ALL forms (active and recently completed)
                active_forms_list = []
                for token, form_data in active_forms_dict.items():
                    # Include all forms except very old completed ones
                    include_form = True
                    
                    # Filter out very old completed forms (older than 10 minutes)
                    if form_data.get('status') == 'completed':
                        try:
                            if form_data.get('completion_time') or form_data.get('last_update'):
                                last_time = form_data.get('completion_time') or form_data.get('last_update')
                                last_update = datetime.fromisoformat(last_time)
                                if (datetime.utcnow() - last_update).total_seconds() > 600:  # 10 minutes
                                    include_form = False
                        except:
                            pass
                    
                    if include_form:
                        form_data['token'] = token  # Ensure token is set
                        active_forms_list.append(form_data)
                
                print(f"✅ Found {len(active_forms_list)} forms for agent {agent_id} (from agent list)")
                return active_forms_list
            
            # Fallback: Search Redis keys (less efficient but more reliable)
            return self._get_agent_forms_from_all_keys(agent_id)
            
        except Exception as e:
            self.logger.error(f"Error getting agent active forms: {e}")
            print(f"❌ Error getting active forms: {e}")
            return []
    
    def _get_agent_forms_from_all_keys(self, agent_id):
        """Fallback method: Search all form progress keys for agent's forms"""
        try:
            # Search for all form progress keys
            keys = self.redis_client.keys("form_progress:*")
            active_forms = []
            
            for key in keys:
                progress_data = self.redis_client.get(key)
                if progress_data:
                    data = json.loads(progress_data)
                    if data.get('agent_id') == str(agent_id):
                        # Include all forms - let the frontend decide what to show
                        token = key.decode().replace('form_progress:', '')
                        data['token'] = token
                        active_forms.append(data)
            
            print(f"✅ Fallback search found {len(active_forms)} forms for agent {agent_id}")
            return active_forms
            
        except Exception as e:
            self.logger.error(f"Error in fallback search: {e}")
            return []
    
    def _get_current_timestamp(self):
        """Get current timestamp"""
        return datetime.utcnow().isoformat()

# Global service instance - initialize without Redis
progress_service = LiveProgressService()

def register_socketio_events(socketio):
    """Register SocketIO events for live progress with form restoration"""
    
    @socketio.on('connect')
    def handle_connect():
        print(f"🔌 Client connected: {current_user.username if current_user.is_authenticated else 'Anonymous'}")
        # Initialize Redis here when we have a proper Flask context
        progress_service._init_redis()
    
    @socketio.on('disconnect')
    def handle_disconnect():
        print(f"🔌 Client disconnected: {current_user.username if current_user.is_authenticated else 'Anonymous'}")
    
    @socketio.on('join_agent_room')
    def handle_join_agent_room(data):
        """Agent joins their room to receive progress updates"""
        if current_user.is_authenticated and current_user.is_agent():
            room = f"agent_{current_user.id}"
            join_room(room)
            print(f"👤 Agent {current_user.username} joined room: {room}")
            emit('joined_room', {'room': room, 'message': 'Successfully joined agent room'})
            
            # Send current active forms immediately
            active_forms = progress_service.get_agent_active_forms(current_user.id)
            emit('active_forms_update', {'forms': active_forms})
        else:
            emit('error', {'message': 'Unauthorized: Only agents can join agent rooms'})
    
    @socketio.on('leave_agent_room')
    def handle_leave_agent_room(data):
        """Agent leaves their room"""
        if current_user.is_authenticated and current_user.is_agent():
            room = f"agent_{current_user.id}"
            leave_room(room)
            print(f"👤 Agent {current_user.username} left room: {room}")
    
    @socketio.on('get_form_progress')
    def handle_get_form_progress(data):
        """NEW: Handle form progress request from customer"""
        token = data.get('token')
        if token:
            print(f"📡 Form progress requested for token: {token}")
            progress_data = progress_service.get_form_progress(token)
            emit('form_progress_response', {
                'success': True,
                'progress': progress_data,
                'token': token
            })
        else:
            emit('form_progress_response', {
                'success': False,
                'error': 'Token required',
                'progress': None
            })
    
    @socketio.on('form_field_update')
    def handle_form_field_update(data):
        """Handle form field updates from customer"""
        token = data.get('token')
        field_name = data.get('field_name')
        field_value = data.get('field_value')
        
        print(f"📝 Form update received - Token: {token}, Field: {field_name}, Value: {field_value}")
        
        if token and field_name:
            # Update progress with correct total fields count
            progress_data = progress_service.update_form_progress(token, field_name, field_value, total_fields=12)
            
            if progress_data and progress_data.get('agent_id'):
                # Emit to agent's room
                agent_room = f"agent_{progress_data['agent_id']}"
                socketio.emit('progress_update', {
                    'token': token,
                    'field_name': field_name,
                    'field_value': field_value,
                    'progress_data': progress_data,
                    'timestamp': progress_data.get('last_update')
                }, room=agent_room)
                
                # Also send updated active forms list
                active_forms = progress_service.get_agent_active_forms(progress_data['agent_id'])
                socketio.emit('active_forms_update', {'forms': active_forms}, room=agent_room)
                
                print(f"📡 Progress update sent to room: {agent_room}")
            else:
                # Fallback to find agent_id
                print(f"⚠️ No agent_id in progress data, trying to find from form link...")
                try:
                    from models.forms import get_form_links_collection
                    
                    form_links = get_form_links_collection()
                    link_data = form_links.find_one({'token': token})
                    
                    if link_data and link_data.get('agent_id'):
                        agent_id = str(link_data['agent_id'])
                        print(f"✅ Found agent_id from form link: {agent_id}")
                        
                        # Update the progress data with agent_id
                        if progress_service.ensure_agent_id_in_progress(token, agent_id):
                            # Get updated progress data
                            updated_progress = progress_service.get_form_progress(token)
                            if updated_progress:
                                agent_room = f"agent_{agent_id}"
                                socketio.emit('progress_update', {
                                    'token': token,
                                    'field_name': field_name,
                                    'field_value': field_value,
                                    'progress_data': updated_progress,
                                    'timestamp': updated_progress.get('last_update')
                                }, room=agent_room)
                                
                                # Also send updated active forms list
                                active_forms = progress_service.get_agent_active_forms(agent_id)
                                socketio.emit('active_forms_update', {'forms': active_forms}, room=agent_room)
                                
                                print(f"📡 Progress update sent to room: {agent_room} (after adding agent_id)")
                    else:
                        print(f"❌ Could not find agent_id for token: {token}")
                except Exception as e:
                    print(f"❌ Error finding agent_id: {e}")
        else:
            print(f"❌ Missing token or field_name in form update")
    
    @socketio.on('get_active_forms')
    def handle_get_active_forms():
        """Get active forms for current agent"""
        if current_user.is_authenticated and current_user.is_agent():
            active_forms = progress_service.get_agent_active_forms(current_user.id)
            emit('active_forms_update', {'forms': active_forms})
            print(f"📋 Sent {len(active_forms)} forms to agent {current_user.username}")
        else:
            emit('error', {'message': 'Unauthorized: Only agents can get active forms'})
    
    @socketio.on('refresh_forms')
    def handle_refresh_forms():
        """Manual refresh of active forms"""
        if current_user.is_authenticated and current_user.is_agent():
            active_forms = progress_service.get_agent_active_forms(current_user.id)
            emit('active_forms_update', {'forms': active_forms})
            print(f"🔄 Refreshed forms for agent {current_user.username}")
    
    print("✅ SocketIO events registered successfully")
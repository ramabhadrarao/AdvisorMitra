# services/live_progress_service.py
# Live form progress tracking service - FIXED

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
        
        # Initialize Redis connection
        try:
            self.redis_client = redis.from_url(current_app.config.get('REDIS_URL', 'redis://localhost:6379/0'))
            self.redis_client.ping()
            print("✅ Redis connected successfully")
        except Exception as e:
            self.logger.warning(f"Redis connection failed: {e}. Live progress will not work.")
            print(f"❌ Redis connection failed: {e}")
            self.redis_client = None
    
    def get_progress_key(self, token):
        """Generate Redis key for form progress"""
        return f"form_progress:{token}"
    
    def update_form_progress(self, token, field_name, field_value, total_fields=13):
        """Update form progress in Redis"""
        if not self.redis_client:
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
                    'status': 'active'
                }
            
            # Update field data
            progress_data['completed_fields'][field_name] = field_value
            progress_data['last_update'] = self._get_current_timestamp()
            
            # Store basic customer info for agent display
            if field_name == 'name' and field_value:
                progress_data['customer_info']['name'] = field_value
            elif field_name == 'email' and field_value:
                progress_data['customer_info']['email'] = field_value
            elif field_name == 'mobile' and field_value:
                progress_data['customer_info']['mobile'] = field_value
            
            # Calculate progress percentage (only count non-empty fields)
            completed_count = len([v for v in progress_data['completed_fields'].values() if v and str(v).strip()])
            progress_data['percentage'] = min(100, (completed_count / total_fields) * 100)
            
            # Store in Redis with 2 hour expiry
            self.redis_client.setex(progress_key, 7200, json.dumps(progress_data))
            
            print(f"✅ Progress updated for {token}: {completed_count}/{total_fields} fields ({progress_data['percentage']:.1f}%)")
            
            return progress_data
            
        except Exception as e:
            self.logger.error(f"Error updating form progress: {e}")
            print(f"❌ Error updating progress: {e}")
            return None
    
    def get_form_progress(self, token):
        """Get current form progress"""
        if not self.redis_client:
            return None
        
        try:
            progress_key = self.get_progress_key(token)
            progress_data = self.redis_client.get(progress_key)
            
            if progress_data:
                return json.loads(progress_data)
            
        except Exception as e:
            self.logger.error(f"Error getting form progress: {e}")
        
        return None
    
    def start_form_session(self, token, agent_id):
        """Initialize form progress tracking"""
        if not self.redis_client:
            print("❌ Redis not available for starting session")
            return
        
        try:
            progress_key = self.get_progress_key(token)
            
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
            print(f"✅ Form session started for token: {token}")
            
        except Exception as e:
            self.logger.error(f"Error starting form session: {e}")
            print(f"❌ Error starting session: {e}")
    
    def complete_form_session(self, token):
        """Mark form as completed"""
        if not self.redis_client:
            return
        
        try:
            progress_key = self.get_progress_key(token)
            progress_data = self.get_form_progress(token)
            
            if progress_data:
                progress_data['status'] = 'completed'
                progress_data['percentage'] = 100
                progress_data['completion_time'] = self._get_current_timestamp()
                
                # Store for 24 hours after completion
                self.redis_client.setex(progress_key, 86400, json.dumps(progress_data))
                print(f"✅ Form session completed for token: {token}")
                
        except Exception as e:
            self.logger.error(f"Error completing form session: {e}")
    
    def get_agent_active_forms(self, agent_id):
        """Get all active forms for an agent"""
        if not self.redis_client:
            return []
        
        try:
            # Search for all form progress keys
            keys = self.redis_client.keys("form_progress:*")
            active_forms = []
            
            for key in keys:
                progress_data = self.redis_client.get(key)
                if progress_data:
                    data = json.loads(progress_data)
                    if (data.get('agent_id') == str(agent_id) and 
                        data.get('status') in ['started', 'active'] and
                        data.get('percentage', 0) < 100):
                        
                        token = key.decode().replace('form_progress:', '')
                        data['token'] = token
                        active_forms.append(data)
            
            print(f"✅ Found {len(active_forms)} active forms for agent {agent_id}")
            return active_forms
            
        except Exception as e:
            self.logger.error(f"Error getting agent active forms: {e}")
            print(f"❌ Error getting active forms: {e}")
            return []
    
    def _get_current_timestamp(self):
        """Get current timestamp"""
        return datetime.utcnow().isoformat()

# Global service instance
progress_service = LiveProgressService()

def register_socketio_events(socketio):
    """Register SocketIO events for live progress"""
    
    @socketio.on('connect')
    def handle_connect():
        print(f"🔌 Client connected: {current_user.username if current_user.is_authenticated else 'Anonymous'}")
    
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
            
            # Send current active forms
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
    
    @socketio.on('form_field_update')
    def handle_form_field_update(data):
        """Handle form field updates from customer"""
        token = data.get('token')
        field_name = data.get('field_name')
        field_value = data.get('field_value')
        
        print(f"📝 Form update received - Token: {token}, Field: {field_name}, Value: {field_value}")
        
        if token and field_name:
            # Update progress
            progress_data = progress_service.update_form_progress(token, field_name, field_value)
            
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
                
                print(f"📡 Progress update sent to room: {agent_room}")
            else:
                print(f"❌ No agent_id found in progress data or update failed")
        else:
            print(f"❌ Missing token or field_name in form update")
    
    @socketio.on('get_active_forms')
    def handle_get_active_forms():
        """Get active forms for current agent"""
        if current_user.is_authenticated and current_user.is_agent():
            active_forms = progress_service.get_agent_active_forms(current_user.id)
            emit('active_forms_update', {'forms': active_forms})
            print(f"📋 Sent {len(active_forms)} active forms to agent {current_user.username}")
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
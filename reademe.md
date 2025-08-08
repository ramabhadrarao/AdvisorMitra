# Financial Planning System - Phase 1

A Flask-based financial planning system with MongoDB backend and Tabler UI frontend.

## Features Implemented (Phase 1)

### Authentication & User Management
- ✅ Login/Logout with Flask-Login
- ✅ Change Password functionality
- ✅ Profile management with image upload
- ✅ Role-based access control (OWNER, ADMIN, AGENT)

### Master Admin (Owner) Features
- ✅ User Management
  - Create users (Admins and Agents)
  - View all users with pagination
  - Activate/Deactivate users
  - Assign plans to agents
- ✅ Plan Management
  - Create subscription plans
  - Edit plan details
  - Activate/Deactivate plans
  - Set period (Monthly/Yearly/Custom)
  - Set PDF generation limits
- ✅ Coupon Management
  - Create discount coupons
  - Auto-generate or manual coupon codes
  - Percentage or fixed amount discounts
  - Set validity periods
  - Usage limits
  - Plan-specific restrictions

### Admin Features
- ✅ View users (Agents and other Admins only)
- ✅ Create new agents
- ✅ View agent activities

### Agent Features
- ✅ Dashboard with plan details
- ✅ View plan expiry and PDF usage
- ✅ Profile management

### API Endpoints
- ✅ RESTful API for all features
- ✅ JSON responses for frontend integration

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd financial_planning_system
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create `.env` file:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Create upload directories:
```bash
mkdir -p static/uploads/profiles
```

6. Start MongoDB:
```bash
# Make sure MongoDB is running on localhost:27017
```

7. Run the application:
```bash
python app.py
```

## Default Credentials
- Username: `admin`
- Password: `admin123`

## Project Structure
```
financial_planning_system/
├── app.py                 # Main application entry
├── config.py             # Configuration settings
├── requirements.txt      # Python dependencies
├── models/              # Database models
│   ├── user.py
│   ├── plan.py
│   └── coupon.py
├── controllers/         # Route controllers
│   ├── auth_controller.py
│   ├── user_controller.py
│   ├── plan_controller.py
│   └── coupon_controller.py
├── services/           # Business logic
│   ├── auth_service.py
│   ├── user_service.py
│   ├── plan_service.py
│   └── coupon_service.py
├── templates/          # HTML templates
│   ├── base.html
│   ├── auth/
│   ├── dashboard/
│   ├── users/
│   ├── plans/
│   └── coupons/
├── static/            # Static files
│   ├── uploads/
│   └── css/
└── utils/            # Helper functions
    ├── decorators.py
    └── helpers.py
```

## API Documentation

### Authentication
- `POST /auth/login` - User login
- `POST /auth/logout` - User logout
- `POST /auth/change-password` - Change password
- `POST /auth/api/login` - API login (returns JSON)
- `POST /auth/api/logout` - API logout
- `POST /auth/api/change-password` - API change password

### Users
- `GET /users/` - List all users
- `GET /users/create` - Create user form
- `POST /users/create` - Create new user
- `GET /users/profile` - View/Edit profile
- `POST /users/<user_id>/toggle-status` - Activate/Deactivate user
- `POST /users/<user_id>/assign-plan` - Assign plan to agent
- `GET /users/api/list` - API list users
- `POST /users/api/create` - API create user
- `GET /users/api/profile` - API get profile
- `PUT /users/api/profile` - API update profile

### Plans
- `GET /plans/` - List all plans
- `GET /plans/create` - Create plan form
- `POST /plans/create` - Create new plan
- `GET /plans/<plan_id>/edit` - Edit plan form
- `POST /plans/<plan_id>/edit` - Update plan
- `POST /plans/<plan_id>/toggle-status` - Activate/Deactivate plan
- `GET /plans/api/list` - API list plans
- `GET /plans/api/active` - API list active plans
- `POST /plans/api/create` - API create plan

### Coupons
- `GET /coupons/` - List all coupons
- `GET /coupons/create` - Create coupon form
- `POST /coupons/create` - Create new coupon
- `GET /coupons/<coupon_id>/edit` - Edit coupon form
- `POST /coupons/<coupon_id>/edit` - Update coupon
- `POST /coupons/<coupon_id>/toggle-status` - Activate/Deactivate coupon
- `GET /coupons/api/list` - API list coupons
- `POST /coupons/api/validate` - API validate coupon

## Next Steps (Future Phases)

### Phase 2 - Form Builder
- Dynamic form creation
- Multiple input types
- Form templates
- Form sharing via links

### Phase 3 - PDF Generation
- Multi-language support (9 languages)
- Template management
- PDF customization
- Watermarking

### Phase 4 - Enhanced Features
- Email/SMS notifications
- Advanced reporting
- Analytics dashboard
- Payment integration

## Technologies Used
- **Backend**: Flask, Flask-Login, Flask-PyMongo
- **Database**: MongoDB
- **Frontend**: Tabler UI (CDN)
- **Authentication**: JWT, bcrypt
- **File Upload**: Pillow

## Security Features
- Password hashing with bcrypt
- Role-based access control
- Session management
- CSRF protection (Flask-WTF)
- File upload validation

## Contributing
Please follow the existing code structure and naming conventions when contributing.

## License
[Your License Here]
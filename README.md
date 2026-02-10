# TechNova💻

# Overview

This is a College Event Registration Portal built with Flask that allows students to register for college events and administrators to manage those events. The system provides separate dashboards for students and administrators, with features for event creation, registration management, and participant tracking.

# System Architecture

## Backend Architecture
- **Framework**: Flask web framework with SQLAlchemy ORM for database operations
- **Database**: PostgreSQL with Flask-SQLAlchemy integration
- **Authentication**: Session-based authentication with password hashing using Werkzeug security utilities
- **Application Structure**: Modular design with separate files for models, routes, and application configuration

## Database Design
- **Student Model**: Stores student information including name, email, roll number, department, and authentication credentials
- **Admin Model**: Simple admin authentication with username and password
- **Event Model**: Contains event details like title, description, date, venue, department, and participant limits
- **Registration Model**: Junction table linking students to events with registration timestamps
- **Relationships**: One-to-many relationships between students/events and registrations with cascade delete

## Frontend Architecture
- **Template Engine**: Jinja2 templating with Flask
- **UI Framework**: Bootstrap 5 with dark theme and Font Awesome icons
- **Responsive Design**: Mobile-first approach with responsive grid layouts
- **User Experience**: Separate dashboards for students and administrators with intuitive navigation

## Security Features
- **Password Security**: Bcrypt password hashing for secure credential storage
- **Session Management**: Flask sessions for user authentication state
- **Input Validation**: Server-side validation for all form inputs
- **Access Control**: Role-based access with separate student and admin authentication flows

## Application Flow
- **Student Journey**: Registration → Login → Event browsing → Event registration → Registration management
- **Admin Journey**: Login → Event creation/management → Participant tracking → Registration oversight
- **Default Setup**: Automatic creation of default admin account on first run

# External Dependencies

## Core Framework Dependencies
- **Flask**: Web application framework
- **Flask-SQLAlchemy**: Database ORM integration
- **Werkzeug**: WSGI utilities and security functions for password hashing

## Frontend Dependencies
- **Bootstrap 5**: CSS framework loaded from CDN with dark theme
- **Font Awesome 6**: Icon library for UI enhancement
- **Custom CSS**: Additional styling for event cards and form elements

## Database
- **PostgreSQL**: Primary database system
- **SQLAlchemy**: Database abstraction layer with declarative base models

## Environment Configuration
- **Environment Variables**: DATABASE_URL for database connection and SESSION_SECRET for session security
- **Development Defaults**: Local PostgreSQL fallback and development session key
- **Deployment Ready**: ProxyFix middleware for production deployment behind reverse proxies

## Session and Security
- **Flask Sessions**: Built-in session management for user authentication
- **Password Hashing**: Werkzeug's security utilities for secure password storage
- **Database Connection**: Connection pooling and health checks configured for reliability

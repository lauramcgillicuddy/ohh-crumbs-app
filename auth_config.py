import streamlit_authenticator as stauth
import yaml
import os

def get_auth_config():
    admin_password = os.getenv('ADMIN_PASSWORD')
    
    if not admin_password:
        import streamlit as st
        st.error("🚨 **Security Error:** ADMIN_PASSWORD environment variable is not set!")
        st.write("**To fix this:**")
        st.write("1. Click the 🔒 Secrets icon in Replit's left sidebar")
        st.write("2. Add a new secret: `ADMIN_PASSWORD`")
        st.write("3. Set a secure password as the value")
        st.write("4. Refresh this page")
        st.stop()
    
    config = {
        'credentials': {
            'usernames': {
                'admin': {
                    'email': 'admin@ohhcrumbs.com',
                    'name': 'Admin',
                    'password': admin_password
                }
            }
        },
        'cookie': {
            'expiry_days': 30,
            'key': os.getenv('SESSION_SECRET', 'ohhcrumbs_secret_key_2024'),
            'name': 'ohhcrumbs_cookie'
        },
        'preauthorized': {
            'emails': []
        }
    }
    return config

def setup_authentication():
    config = get_auth_config()
    
    authenticator = stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days'],
        auto_hash=True
    )
    
    return authenticator

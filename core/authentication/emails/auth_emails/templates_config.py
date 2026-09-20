"""
Static definition table for every seedable authentication email template.
"""

EMAIL_TEMPLATE_DEFINITIONS = [
    {
        "key": "welcome_email",
        "subject_key": "email_template_welcome_subject",
        "body_key": "email_template_welcome_body",
        "description_key": "email_template_welcome_desc",
    },
    {
        "key": "email_verification",
        "subject_key": "email_template_verification_subject",
        "body_key": "email_template_verification_body",
        "description_key": "email_template_verification_desc",
    },
    {
        "key": "password_reset",
        "subject_key": "email_template_password_reset_subject",
        "body_key": "email_template_password_reset_body",
        "description_key": "email_template_password_reset_desc",
    },
]

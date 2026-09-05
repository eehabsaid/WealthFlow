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
        "key": "admin_approval_request",
        "subject_key": "email_template_admin_approval_subject",
        "body_key": "email_template_admin_approval_body",
        "description_key": "email_template_admin_approval_desc",
    },
    {
        "key": "account_approved",
        "subject_key": "email_template_account_approved_subject",
        "body_key": "email_template_account_approved_body",
        "description_key": "email_template_account_approved_desc",
    },
    {
        "key": "account_rejected",
        "subject_key": "email_template_account_rejected_subject",
        "body_key": "email_template_account_rejected_body",
        "description_key": "email_template_account_rejected_desc",
    },
    {
        "key": "password_reset",
        "subject_key": "email_template_password_reset_subject",
        "body_key": "email_template_password_reset_body",
        "description_key": "email_template_password_reset_desc",
    },
]

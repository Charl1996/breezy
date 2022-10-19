import requests
from configs import MAILGUN_API_KEY, MAILGUN_URL
from logger import log


def mail(from_address, recipients=[], subject=None, body=None, attachment_info=None):
    data = {
        "from": from_address,
        "to": recipients,
        "subject": subject,
        "text": body,
    }
    files = None

    if attachment_info:
        files = [("attachment", (attachment_info['name'], open(attachment_info['path'], 'rb').read(), 'text/csv'))]

    res = requests.post(
        f'{MAILGUN_URL}messages',
        data=data,
        files=files,
        auth=('api', MAILGUN_API_KEY)
    )

    if res.status_code != 200:
        log(f'Failed to send email with subject: {subject}')

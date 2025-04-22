from django.dispatch import Signal

# Signal sent when a new email is received and processed
# Provides: email (IncomingEmail instance)
email_received = Signal()

# Signal sent when an email with attachments is received
# Provides: email (IncomingEmail instance), attachments (list of EmailAttachment instances)
email_with_attachments_received = Signal()

# Signal sent when an email triggers a meeting creation
# Provides: email (IncomingEmail instance), meeting (MeetingTranscript instance)
meeting_email_received = Signal() 
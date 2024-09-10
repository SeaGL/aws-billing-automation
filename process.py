#!/usr/bin/env python3

import ssl, os, email, io, time, sys
from imaplib import IMAP4_SSL
import requests

global_errors = False

print("Starting program.")

s = requests.Session()
s.headers[
    "User-Agent"
] = "github.com/SeaGL/aws-billing-automation - let me email receipts like Brex does so I can delete this script!"
s.headers["Authorization"] = f'Bearer {os.environ["PEX_BEARER_TOKEN"]}'
print("Pex bearer token retrieved and Requests configured.")

host = os.environ["IMAP_HOST"]
print(f"Connecting to IMAP host {host}.")
with IMAP4_SSL(host) as C:
    print("Connected to IMAP host.")

    C.login(os.environ["IMAP_USERNAME"], os.environ["IMAP_PASSWORD"])
    print("Logged in successfully.")

    C.select("INBOX")
    _, res = C.search(None, 'CC aws-billing@seagl.org UNSEEN HEADER Subject "Amazon Web Services Invoice Available"')
    print(f"Executed search; got IDs {res}.")
    msg_ids = res[0].split()
    for i in msg_ids:
        print(f"Processing message ID {i}.")
        _, data = C.fetch(i, "(BODY.PEEK[])")
        msg = email.message_from_bytes(data[0][1], _class=email.message.EmailMessage)
        # iter_attachments() returns a generator and we only care about the first value
        part = next(msg.iter_attachments())
        assert part.get_content_type() == "application/octet-stream"
        assert part.get_filename()[:7] == "invoice"
        assert part.get_filename()[-4:] == ".pdf"

        print(f"Retrieved attachment {part.get_filename()}; uploading to Pex...")

        files = {
            "file": (
                part.get_filename(),
                io.BytesIO(part.get_payload(decode=True)),
                "application/pdf",
            )
        }
        upload_r = s.post(
            "https://coreapi.pexcard.com/internal/v4/TransactionMetadata/Business/Attachment/Upload",
            files=files,
        )
        upload_r.raise_for_status()
        assert "id" in upload_r.json()
        assert upload_r.json()['type'] == "Pdf"

        print("Posted attachment to Pex.")

        id_r = s.get(
            "https://coreapi.pexcard.com/internal/v4/TransactionMetadata/User/Attachments/Unmatched"
        )
        id_r.raise_for_status()
        pex_id_json = id_r.json()[0]
        pex_id = pex_id_json["transactionRelationId"]
        if pex_id_json["suggested"]:
            assert pex_id_json["suggested"]["suggestedStatus"] == "Processing"

        print("Retrieved Pex relation ID.")

        tries = 0
        success = False
        no_match = False
        while tries < 12 and not success:
            status_r = s.get(
                f"https://coreapi.pexcard.com/internal/v4/TransactionMetadata/User/Attachments/{pex_id}"
            )
            status_r.raise_for_status()

            suggested = status_r.json()["suggested"]
            if not suggested:
                print(f"WARNING: file {part.get_filename()} uploaded to Pex, but could not be matched.", file=sys.stderr)
                no_match = True
                global_errors = True
                break

            status = status_r.json()["suggested"]["suggestedStatus"]
            if status == "Processing":
                print("Pex reports relation still processing...")
                time.sleep(10)
                tries += 1
            elif status == "Success":
                print("Pex successfully processed transaction relation.")
                success = True
            else:
                raise NotImplementedError(f"Got status: {status}")

        if success:
            print(
                f"Successfully submitted attachment for email message ID {i}; marking as read... ",
                end="",
            )
            C.store(i, "+FLAGS", "\Seen")
            print("done.")
        elif no_match:
            print("Encountered problems processing attachment for email message ID {i}, but marking as read anyway - file made it to Pex... ", end='')
            C.store(i, "+FLAGS", "\Seen")
            print("done.")
        else:
            print(
                f"Failed to process email message ID {i}; bailing out.", file=sys.stderr
            )
            exit(1)

if global_errors:
    print("Done, with errors.")
    exit(1)

print("Done.")

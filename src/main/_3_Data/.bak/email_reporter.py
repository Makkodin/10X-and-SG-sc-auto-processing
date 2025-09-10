import os
import zipfile
import pandas as pd
from typing import List, Optional, Dict
import configparser
from zeep import Client, Settings
from zeep.transports import Transport
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import base64
from requests import Session
from requests.auth import HTTPBasicAuth
import urllib3
from urllib3.exceptions import InsecureRequestWarning

# Disable SSL warnings for testing
urllib3.disable_warnings(InsecureRequestWarning)

class EmailReporter:
    def __init__(self, exchange_config: Dict[str, str]):
        """
        Initialize email reporter using SOAP API via WSDL
        :param exchange_config: Exchange configuration as dictionary
        """
        self.exchange_config = exchange_config
        self.client = None
        self.session = None
    
    def create_soap_client(self):
        """
        Create SOAP client for Exchange Web Services
        """
        try:
            # Create session with authentication
            self.session = Session()
            self.session.auth = HTTPBasicAuth(
                self.exchange_config['sender_email'],
                self.exchange_config['sender_password']
            )
            self.session.verify = False  # Disable SSL verification for testing
            
            # Client settings
            settings = Settings(
                strict=False,
                xml_huge_tree=True,
                extra_http_headers={
                    'Content-Type': 'text/xml; charset=utf-8',
                    'User-Agent': 'Python-SOAP-Client'
                }
            )
            
            transport = Transport(session=self.session)
            
            # Create WSDL client
            self.client = Client(
                wsdl=self.exchange_config['wsdl_url'],
                settings=settings,
                transport=transport
            )
            
            print("✅ SOAP client created successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error creating SOAP client: {e}")
            return False
    
    def create_archive(self, source_dir: str, archive_name: str) -> str:
        """
        Create ZIP archive from all HTML and PNG files in directory
        """
        archive_path = os.path.join(source_dir, archive_name)
        
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(source_dir):
                for file in files:
                    if file.endswith(('.html', '.png', '.csv')):
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, source_dir)
                        zipf.write(file_path, arcname)
        
        return archive_path
    
    def format_statistics_table(self, df: pd.DataFrame) -> str:
        """
        Format statistics table for better readability
        """
        formatted_df = df.copy()

        for col in formatted_df.columns:
            if formatted_df[col].dtype in ['float64', 'int64']:
                # For sample_id column, remove commas
                if col.lower() == 'sample_id':
                    formatted_df[col] = formatted_df[col].apply(lambda x: f"{x:.0f}" if pd.notna(x) else "N/A")
                # For percentage columns
                elif any('percent' in col.lower() or '%' in col.lower() for col in formatted_df.columns):
                    formatted_df[col] = formatted_df[col].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "N/A")
                # For large numbers (except sample_id)
                elif formatted_df[col].max() > 1000:
                    formatted_df[col] = formatted_df[col].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "N/A")
                # For regular numbers
                else:
                    formatted_df[col] = formatted_df[col].apply(lambda x: f"{x:.0f}" if pd.notna(x) else "N/A")

        html_table = formatted_df.to_html(
            index=False, 
            classes='statistics-table',
            border=1,
            justify='left'
        )
        return html_table
    
    def create_email_body(self, flowcell: str, ceph_paths: List[str], 
                         statistics_csv_path: str) -> str:
        """
        Create email body with statistics table
        """
        try:
            df = pd.read_csv(statistics_csv_path)
            stats_table = self.format_statistics_table(df)
        except Exception as e:
            stats_table = f"<p>Error loading statistics: {e}</p>"
        
        email_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; color: #333; }}
                .container {{ max-width: 1200px; margin: 0 auto; }}
                .header {{ background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
                .statistics-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 14px; }}
                .statistics-table th {{ background-color: #e9ecef; padding: 12px; text-align: left; font-weight: bold; border: 1px solid #dee2e6; }}
                .statistics-table td {{ padding: 10px; border: 1px solid #dee2e6; }}
                .statistics-table tr:nth-child(even) {{ background-color: #f8f9fa; }}
                .statistics-table tr:hover {{ background-color: #e9ecef; }}
                .info-box {{ background-color: #e7f3ff; border-left: 4px solid #007bff; padding: 15px; margin: 15px 0; border-radius: 3px; }}
                .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; color: #6c757d; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header"><h2>Автоматический отчет по обработке ячейки {flowcell}</h2></div>
                <p>Добрый день,</p>
                <div class="info-box">
                    <p>Обработка ячейки <strong>{flowcell}</strong> успешно завершена.</p>
                    <p><strong>Расположение данных:</strong><br>
                    {', '.join([f'{path}/{flowcell}' for path in ceph_paths])}</p>
                </div>
                <h3>Статистика по ячейке:</h3>
                {stats_table}
                <div class="footer">
                    <p>Это письмо было отправлено автоматически. Пожалуйста, не отвечайте на него.</p>
                    <p>С уважением,<br>Автоматизированная система обработки данных</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        
        return email_body
    
    def send_email_soap(self, recipient_emails: List[str], subject: str, 
                       body: str, attachment_path: Optional[str] = None) -> bool:
        """
        Send email via SOAP API using WSDL
        """
        try:
            if not self.client:
                if not self.create_soap_client():
                    return False
            
            # Read attachment if exists
            attachment_data = None
            attachment_name = None
            if attachment_path and os.path.exists(attachment_path):
                with open(attachment_path, 'rb') as f:
                    attachment_data = base64.b64encode(f.read()).decode('utf-8')
                attachment_name = os.path.basename(attachment_path)
            
            # Prepare SOAP request data
            soap_request = {
                'From': {'Address': self.exchange_config['sender_email']},
                'ToRecipients': [{'Mailbox': {'EmailAddress': email}} for email in recipient_emails],
                'Subject': subject,
                'Body': {
                    'BodyType': 'HTML',
                    '_value_1': body
                }
            }
            
            # Add attachment if exists
            if attachment_data:
                soap_request['Attachments'] = {
                    'FileAttachment': {
                        'Name': attachment_name,
                        'Content': attachment_data,
                        'ContentType': 'application/zip'
                    }
                }
            
            # Call SOAP method to send email
            # Method depends on your WSDL structure
            try:
                # Try to find appropriate method
                response = self.client.service.CreateItem(
                    Message=soap_request
                )
                print("✅ Email sent via SOAP API")
                return True
                
            except AttributeError:
                # If CreateItem method not found, try SendEmail
                try:
                    response = self.client.service.SendEmail(**soap_request)
                    print("✅ Email sent via SOAP API")
                    return True
                except Exception as e:
                    print(f"❌ Error calling SOAP method SendEmail: {e}")
                    return False
                    
        except Exception as e:
            print(f"❌ Error sending via SOAP: {e}")
            return False
    
    def send_email_smtp_fallback(self, recipient_emails: List[str], subject: str, 
                               body: str, attachment_path: Optional[str] = None) -> bool:
        """
        Fallback method for sending via SMTP if SOAP fails
        """
        try:
            msg = MIMEMultipart()
            msg['From'] = self.exchange_config['sender_email']
            msg['To'] = ', '.join(recipient_emails)
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'html'))
            
            if attachment_path and os.path.exists(attachment_path):
                with open(attachment_path, 'rb') as attachment:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename="{os.path.basename(attachment_path)}"'
                    )
                    msg.attach(part)
            
            # Use SMTP as fallback
            import smtplib
            with smtplib.SMTP(self.exchange_config.get('smtp_server', 'mail2.cspfmba.ru'), 
                             self.exchange_config.get('smtp_port', 587)) as server:
                server.starttls()
                server.login(self.exchange_config['sender_email'], 
                            self.exchange_config['sender_password'])
                server.sendmail(self.exchange_config['sender_email'], 
                               recipient_emails, msg.as_string())
            
            print("✅ Email sent via SMTP (fallback)")
            return True
            
        except Exception as e:
            print(f"❌ Error sending via SMTP: {e}")
            return False

def load_exchange_config(config_path: str, sender_email: str, sender_password: str) -> Dict[str, str]:
    """
    Load Exchange configuration from file, overriding email and password
    """
    config = configparser.ConfigParser()
    
    try:
        config.read(config_path)
        
        if 'EXCHANGE' not in config:
            raise ValueError("[EXCHANGE] section not found")
        
        return {
            'sender_email': sender_email,  # Use provided email
            'sender_password': sender_password,  # Use provided password
            'wsdl_url': config['EXCHANGE'].get('wsdl_url', 'https://mail2.cspfmba.ru:444/EWS/Services.wsdl'),
            'smtp_server': config['EXCHANGE'].get('smtp_server', 'mail2.cspfmba.ru'),
            'smtp_port': config['EXCHANGE'].get('smtp_port', '587'),
            'ews_url': config['EXCHANGE'].get('ews_url', 'https://mail2.cspfmba.ru:444/EWS/Exchange.asmx')
        }
        
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        return {}

def load_recipients_config(config_path: str) -> List[str]:
    """
    Load recipients list from configuration file
    """
    config = configparser.ConfigParser()
    
    try:
        config.read(config_path)
        
        if 'RECIPIENTS' not in config:
            raise ValueError("[RECIPIENTS] section not found")
        
        emails_str = config['RECIPIENTS'].get('emails', '')
        emails = [email.strip() for email in emails_str.split(',') if email.strip()]
        
        return emails
        
    except Exception as e:
        print(f"❌ Error loading recipients list: {e}")
        return []

def archive_and_send_report(sum_path: str, flowcell: str, ceph_paths: List[str],
                           config_path: str, sender_email: str, sender_password: str,
                           dry_run: bool = False) -> bool:
    """
    Main function for archiving and sending report
    """
    try:
        if not os.path.exists(sum_path):
            print(f"❌ Directory {sum_path} does not exist")
            return False
        
        stats_csv_path = os.path.join(sum_path, f"{flowcell}_statistics_summary.csv")
        if not os.path.exists(stats_csv_path):
            print(f"❌ Statistics file not found: {stats_csv_path}")
            return False
        
        # Load configuration, passing email and password as parameters
        exchange_config = load_exchange_config(config_path, sender_email, sender_password)
        if not exchange_config:
            print("❌ Failed to load configuration")
            return False
        
        recipient_emails = load_recipients_config(config_path)
        if not recipient_emails:
            print("❌ Failed to load recipients list")
            return False
        
        if dry_run:
            print("🔬 TEST MODE")
            print(f"📁 Directory: {sum_path}")
            print(f"🔬 Flowcell: {flowcell}")
            print(f"📧 Sender: {sender_email}")
            print(f"📧 Recipients: {recipient_emails}")
            return True
        
        reporter = EmailReporter(exchange_config)
        
        # Create archive
        archive_name = f"{flowcell}_reports.zip"
        print(f"🕒 Creating archive {archive_name}...")
        archive_path = reporter.create_archive(sum_path, archive_name)
        print(f"✅ Archive created: {archive_path}")
        
        # Create email body
        print("🕒 Creating email body...")
        email_body = reporter.create_email_body(flowcell, ceph_paths, stats_csv_path)
        
        # Send email
        subject = f"Flowcell {flowcell} processing completed"
        print(f"🕒 Sending email to recipients: {recipient_emails}...")
        
        # Try to send via SOAP
        success = reporter.send_email_soap(
            recipient_emails=recipient_emails,
            subject=subject,
            body=email_body,
            attachment_path=archive_path
        )
        
        # If SOAP fails, try SMTP
        if not success:
            print("⚠️ SOAP failed, trying SMTP...")
            success = reporter.send_email_smtp_fallback(
                recipient_emails=recipient_emails,
                subject=subject,
                body=email_body,
                attachment_path=archive_path
            )
        
        return success
            
    except Exception as e:
        print(f"❌ Critical error: {e}")
        return False
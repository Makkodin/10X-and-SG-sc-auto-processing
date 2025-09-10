import os
import zipfile
import pandas as pd
from typing import List, Optional, Dict, Tuple
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
import math
import shutil

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
    
    def get_files_to_archive(self, source_dir: str) -> List[Tuple[str, str]]:
        """
        Get list of files to archive with their sizes
        Returns: list of (file_path, relative_path) tuples
        """
        files = []
        for root, _, filenames in os.walk(source_dir):
            for file in filenames:
                if file.endswith(('.html', '.png', '.csv')):
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, source_dir)
                    files.append((file_path, relative_path))
        return files
    
    def create_single_archive(self, source_dir: str, archive_name: str) -> str:
        """
        Create single ZIP archive with all files
        """
        archive_path = os.path.join(source_dir, archive_name)
        files = self.get_files_to_archive(source_dir)
        
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path, relative_path in files:
                zipf.write(file_path, relative_path)
        
        return archive_path
    
    def split_files_into_parts(self, source_dir: str, max_size_mb: int = 25) -> List[List[Tuple[str, str]]]:
        """
        Split files into parts where each part is <= max_size_mb
        Returns: list of file groups for multi-part archives
        """
        files = self.get_files_to_archive(source_dir)
        max_size_bytes = max_size_mb * 1024 * 1024
        
        # Calculate total size of all files
        total_size = sum(os.path.getsize(fp) for fp, _ in files)
        
        # If total size is less than max, no need to split
        if total_size <= max_size_bytes:
            return [files]  # Return single group
        
        # Calculate how many parts we need
        num_parts = math.ceil(total_size / max_size_bytes)
        target_part_size = total_size / num_parts
        
        # Sort files by size (largest first for better distribution)
        files_with_size = [(fp, rp, os.path.getsize(fp)) for fp, rp in files]
        files_with_size.sort(key=lambda x: x[2], reverse=True)
        
        file_groups = [[] for _ in range(num_parts)]
        group_sizes = [0] * num_parts
        
        # Distribute files to groups using greedy algorithm
        for file_path, relative_path, file_size in files_with_size:
            # Find the group with smallest current size that can accommodate this file
            best_group = None
            min_size = float('inf')
            
            for i in range(num_parts):
                if group_sizes[i] + file_size <= max_size_bytes and group_sizes[i] < min_size:
                    best_group = i
                    min_size = group_sizes[i]
            
            # If no group can accommodate this file (file too large), put it in smallest group
            if best_group is None:
                best_group = group_sizes.index(min(group_sizes))
            
            file_groups[best_group].append((file_path, relative_path))
            group_sizes[best_group] += file_size
        
        return file_groups
    
    def create_multi_part_archives(self, source_dir: str, base_archive_name: str, 
                                 file_groups: List[List[Tuple[str, str]]]) -> List[str]:
        """
        Create multiple archive parts from file groups
        """
        archive_paths = []
        
        for i, file_group in enumerate(file_groups, 1):
            archive_name = f"{base_archive_name}_part{i}_of{len(file_groups)}.zip"
            archive_path = os.path.join(source_dir, archive_name)
            
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path, relative_path in file_group:
                    zipf.write(file_path, relative_path)
            
            archive_paths.append(archive_path)
            print(f"✅ Created part {i}/{len(file_groups)}: {archive_name} "
                  f"({os.path.getsize(archive_path) / (1024 * 1024):.1f} MB)")
        
        return archive_paths

    
    def format_statistics_table(self, df: pd.DataFrame) -> str:
        formatted_df = df.copy()
    
        for col in formatted_df.columns:
            if formatted_df[col].dtype in ['float64', 'int64']:
                if 'fraction of high-quality fragments overlapping peaks' in col.lower():
                    formatted_df[col] = formatted_df[col].apply(
                        lambda x: f"{x * 100:.1f}%" if pd.notna(x) and isinstance(x, (int, float)) else ""  # Изменено на пустую строку
                    )
                elif col.lower() == 'sample_id':
                    formatted_df[col] = formatted_df[col].apply(lambda x: f"{x:.0f}" if pd.notna(x) else "")  # Изменено на пустую строку
                elif any(keyword in col.lower() for keyword in ['percent', '%', 'percentage']):
                    formatted_df[col] = formatted_df[col].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "")  # Изменено на пустую строку
                elif formatted_df[col].max() > 1000:
                    formatted_df[col] = formatted_df[col].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "")  # Изменено на пустую строку
                else:
                    formatted_df[col] = formatted_df[col].apply(lambda x: f"{x:.0f}" if pd.notna(x) else "")  # Изменено на пустую строку
            elif formatted_df[col].dtype == 'object':
                if 'fraction of high-quality fragments overlapping peaks' in col.lower():
                    try:
                        numeric_values = pd.to_numeric(formatted_df[col], errors='coerce')
                        formatted_df[col] = numeric_values.apply(
                            lambda x: f"{x * 100:.1f}%" if pd.notna(x) else ""  # Изменено на пустую строку
                        )
                    except:
                        pass
                # Добавляем обработку для строковых значений "N/A"
                formatted_df[col] = formatted_df[col].apply(
                    lambda x: "" if pd.isna(x) or str(x).strip().upper() == "N/A" else x
                )
    
        # Дополнительная обработка для замены "N/A" на пустые строки во всей таблице
        formatted_df = formatted_df.applymap(
            lambda x: "" if pd.isna(x) or str(x).strip().upper() == "N/A" else x
        )
    
        html_table = formatted_df.to_html(
            index=False, 
            classes='statistics-table',
            border=1,
            justify='left',
            escape=False
        )
        return html_table
        
    def create_email_body(self, flowcell: str, ceph_paths: List[str], 
                         statistics_csv_path: str, part_number: int = None, 
                         total_parts: int = None) -> str:
        """
        Create email body with statistics table
        """
        try:
            df = pd.read_csv(statistics_csv_path)
            stats_table = self.format_statistics_table(df)
        except Exception as e:
            stats_table = f"<p>Error loading statistics: {e}</p>"
        
        # Add part information if this is a multi-part email
        part_info = ""
        if part_number is not None and total_parts is not None:
            if part_number == 1:
                part_info = f"<div class='info-box'><p><strong>Часть {part_number} из {total_parts}</strong> - Основная статистика</p></div>"
            else:
                part_info = f"<div class='info-box'><p><strong>Часть {part_number} из {total_parts}</strong> - Дополнительные данные</p></div>"
        
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
                {part_info}
                <div class="info-box">
                    <p>Обработка ячейки <strong>{flowcell}</strong> успешно завершена.</p>
                    <p><strong>Расположение данных:</strong><br>
                    {', '.join([f'{path}/{flowcell}' for path in ceph_paths])}</p>
                </div>
                {stats_table if part_number == 1 or part_number is None else ''}
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
            try:
                response = self.client.service.CreateItem(Message=soap_request)
                print("✅ Email sent via SOAP API")
                return True
            except AttributeError:
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
            'sender_email': sender_email,
            'sender_password': sender_password,
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
                           dry_run: bool = False, max_archive_size_mb: int = 25) -> bool:
    """
    Main function for archiving and sending report with size limit handling
    """
    try:
        if not os.path.exists(sum_path):
            print(f"❌ Directory {sum_path} does not exist")
            return False
        
        stats_csv_path = os.path.join(sum_path, f"{flowcell}_statistics_summary.csv")
        if not os.path.exists(stats_csv_path):
            print(f"❌ Statistics file not found: {stats_csv_path}")
            return False
        
        # Load configuration
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
        
        # Step 1: Create single archive first
        single_archive_name = f"{flowcell}_reports.zip"
        print(f"🕒 Creating single archive: {single_archive_name}")
        single_archive_path = reporter.create_single_archive(sum_path, single_archive_name)
        
        # Check archive size
        archive_size_mb = os.path.getsize(single_archive_path) / (1024 * 1024)
        print(f"📊 Archive size: {archive_size_mb:.1f} MB (limit: {max_archive_size_mb} MB)")
        
        archive_paths = []
        
        if archive_size_mb <= max_archive_size_mb:
            # Single archive is within limit
            print("✅ Single archive is within size limit")
            archive_paths = [single_archive_path]
            total_parts = 1
        else:
            # Archive is too big, need to split into parts
            print("⚠️ Archive exceeds size limit, splitting into parts...")
            
            # Remove the single archive since we'll create multiple parts
            os.remove(single_archive_path)
            print("🧹 Removed oversized single archive")
            
            # Split files into optimal groups
            file_groups = reporter.split_files_into_parts(sum_path, max_archive_size_mb)
            total_parts = len(file_groups)
            
            print(f"📦 Splitting into {total_parts} part(s)")
            
            # Create multi-part archives
            archive_paths = reporter.create_multi_part_archives(
                sum_path, f"{flowcell}_reports", file_groups
            )
        
        print(f"📦 Found {len(archive_paths)} archive part(s) to send")
        
        success_count = 0
        
        for part_number, archive_path in enumerate(archive_paths, 1):
            # Get actual archive size
            part_size_mb = os.path.getsize(archive_path) / (1024 * 1024)
            print(f"📦 Processing part {part_number}/{len(archive_paths)}: "
                  f"{os.path.basename(archive_path)} ({part_size_mb:.1f} MB)")
            
            # Create email body
            print("🕒 Creating email body...")
            if part_number == 1:
                # First part includes statistics table
                email_body = reporter.create_email_body(
                    flowcell, ceph_paths, stats_csv_path, part_number, len(archive_paths)
                )
                subject = f"Flowcell {flowcell} processing completed - Part {part_number}/{len(archive_paths)}"
            else:
                # Subsequent parts only include basic info
                email_body = reporter.create_email_body(
                    flowcell, ceph_paths, stats_csv_path, part_number, len(archive_paths)
                )
                subject = f"Flowcell {flowcell} processing completed - Part {part_number}/{len(archive_paths)} (Additional Data)"
            
            # Send email
            print(f"🕒 Sending email part {part_number}/{len(archive_paths)}...")
            
            # Try to send via SOAP
            #success = reporter.send_email_soap(
            #    recipient_emails=recipient_emails,
            #    subject=subject,
            #    body=email_body,
            #    attachment_path=archive_path
            #)
            success =   None
            # If SOAP fails, try SMTP
            if not success:
                print("🕒 Trying SMTP...")
                success = reporter.send_email_smtp_fallback(
                    recipient_emails=recipient_emails,
                    subject=subject,
                    body=email_body,
                    attachment_path=archive_path
                )
            
            if success:
                success_count += 1
                print(f"✅ Successfully sent part {part_number}/{len(archive_paths)}")
            
            # Clean up temporary archive
            try:
                os.remove(archive_path)
                print(f"🧹 Cleaned up temporary archive: {archive_path}")
            except Exception as e:
                print(f"⚠️ Warning: Could not clean up archive {archive_path}: {e}")
        
        # Check if all parts were sent successfully
        if success_count == len(archive_paths):
            print(f"✅ All {len(archive_paths)} email part(s) sent successfully!")
            return True
        else:
            print(f"⚠️ Only {success_count} out of {len(archive_paths)} email part(s) were sent successfully")
            return False
            
    except Exception as e:
        print(f"❌ Critical error: {e}")
        return False
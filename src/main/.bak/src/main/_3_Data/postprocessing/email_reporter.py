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
			
			print("✅[Email report] SOAP client created successfully")
			return True
			
		except Exception as e:
			print(f"❌[Email report] Error creating SOAP client: {e}")
			return False
	
	def get_files_to_archive(self, source_dir: str) -> List[Tuple[str, str, str]]:
		"""
		Get list of files to archive with their sizes and categories
		Returns: list of (file_path, relative_path, file_type) tuples
		file_type: 'html', 'png', 'csv', or 'other'
		"""
		files = []
		for root, _, filenames in os.walk(source_dir):
			for file in filenames:
				if file.endswith(('.html', '.png', '.csv')):
					file_path = os.path.join(root, file)
					relative_path = os.path.relpath(file_path, source_dir)
					
					# Categorize files
					if file.endswith('.html'):
						file_type = 'html'
					elif file.endswith('.png'):
						file_type = 'png'
					elif file.endswith('.csv'):
						file_type = 'csv'
					else:
						file_type = 'other'
					
					files.append((file_path, relative_path, file_type))
		return files
	
	def create_single_archive(self, source_dir: str, archive_name: str) -> str:
		"""
		Create single ZIP archive with all files
		"""
		archive_path = os.path.join(source_dir, archive_name)
		files = self.get_files_to_archive(source_dir)
		
		with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
			for file_path, relative_path, _ in files:
				zipf.write(file_path, relative_path)
		
		return archive_path
	
	def split_files_by_category(self, source_dir: str, max_size_mb: int = 25) -> Tuple[List[List[Tuple[str, str]]], List[List[Tuple[str, str]]]]:
		"""
		Split files into HTML archives and other files archives
		Returns: (html_file_groups, other_file_groups)
		"""
		files = self.get_files_to_archive(source_dir)
		max_size_bytes = max_size_mb * 1024 * 1024
		
		# Separate HTML files from other files
		html_files = [(fp, rp) for fp, rp, ft in files if ft == 'html']
		other_files = [(fp, rp) for fp, rp, ft in files if ft != 'html']
		
		# Calculate total sizes
		html_total_size = sum(os.path.getsize(fp) for fp, _ in html_files)
		other_total_size = sum(os.path.getsize(fp) for fp, _ in other_files)
		
		print(f"📊[Email report] HTML files: {len(html_files)} files, {html_total_size / (1024 * 1024):.1f} MB")
		print(f"📊[Email report] Other files: {len(other_files)} files, {other_total_size / (1024 * 1024):.1f} MB")
		
		# Split HTML files into groups
		html_file_groups = self._split_file_group(html_files, max_size_bytes, "HTML")
		
		# Split other files into groups
		other_file_groups = self._split_file_group(other_files, max_size_bytes, "other files")
		
		return html_file_groups, other_file_groups
	
	def _split_file_group(self, files: List[Tuple[str, str]], max_size_bytes: int, group_name: str) -> List[List[Tuple[str, str]]]:
		"""
		Split a group of files into parts where each part is <= max_size_bytes
		"""
		if not files:
			return []
		
		total_size = sum(os.path.getsize(fp) for fp, _ in files)
		
		# If total size is less than max, no need to split
		if total_size <= max_size_bytes:
			return [files]
		
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
		
		print(f"📦[Email report] Split {group_name} into {num_parts} part(s)")
		for i, group in enumerate(file_groups):
			group_size = sum(os.path.getsize(fp) for fp, _ in group)
			print(f"📦[Email report] Part {i+1}: {len(group)} files, {group_size / (1024 * 1024):.1f} MB")
		
		return file_groups
	
	def create_category_archives(self, source_dir: str, base_archive_name: str, 
							   html_file_groups: List[List[Tuple[str, str]]], 
							   other_file_groups: List[List[Tuple[str, str]]]) -> List[str]:
		"""
		Create archives for HTML files and other files separately
		"""
		archive_paths = []
		
		# Create HTML archives
		for i, file_group in enumerate(html_file_groups, 1):
			if len(html_file_groups) == 1:
				archive_name = f"{base_archive_name}_reports_html.zip"
			else:
				archive_name = f"{base_archive_name}_reports_html_part{i}_of{len(html_file_groups)}.zip"
			
			archive_path = os.path.join(source_dir, archive_name)
			
			with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
				for file_path, relative_path in file_group:
					zipf.write(file_path, relative_path)
			
			archive_paths.append(archive_path)
			archive_size = os.path.getsize(archive_path) / (1024 * 1024)
			print(f"✅[Email report] Created HTML archive: {archive_name} ({archive_size:.1f} MB)")
		
		# Create other files archives
		for i, file_group in enumerate(other_file_groups, 1):
			if len(other_file_groups) == 1:
				archive_name = f"{base_archive_name}_other_files.zip"
			else:
				archive_name = f"{base_archive_name}_other_files_part{i}_of{len(other_file_groups)}.zip"
			
			archive_path = os.path.join(source_dir, archive_name)
			
			with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
				for file_path, relative_path in file_group:
					zipf.write(file_path, relative_path)
			
			archive_paths.append(archive_path)
			archive_size = os.path.getsize(archive_path) / (1024 * 1024)
			print(f"✅[Email report] Created other files archive: {archive_name} ({archive_size:.1f} MB)")
		
		return archive_paths

	def format_statistics_table(self, df: pd.DataFrame) -> str:
		formatted_df = df.copy()
	
		def format_number(x):
			"""Форматирует число согласно требованиям"""
			if pd.isna(x) or str(x).strip().upper() == "N/A":
				return ""

			if isinstance(x, str):
				x_clean = x.replace(',', '').replace(' ', '')
				try:
					x_num = float(x_clean)
					if '%' in x:
						return f"{x_num:.4f}%".replace('.', ',')
					else:
						x = x_num
				except (ValueError, TypeError):
					return x

			if isinstance(x, (int, float)):
				if x == int(x):
					return f"{int(x)}"
				else:
					return f"{x:.3f}".replace('.', ',')

			return x

		# Определяем первую колонку, содержащую "sample" в названии
		sample_columns = [col for col in formatted_df.columns if 'sample' in str(col).lower()]
	
		# Если нашли колонку(ы) с "sample", сохраняем данные в них без форматирования
		# (или применяем только базовую обработку NaN/N/A)
		for col in formatted_df.columns:
			if col in sample_columns:
				# Для sample колонок: только чистим NaN/N/A, но сохраняем исходные значения
				formatted_df[col] = formatted_df[col].apply(
					lambda x: "" if pd.isna(x) or str(x).strip().upper() == "N/A" else str(x)
				)
			else:
				# Для всех остальных колонок применяем полное форматирование
				formatted_df[col] = formatted_df[col].apply(format_number)
	
				# Дополнительное форматирование для процентных колонок
				if any(keyword in col.lower() for keyword in ['gex reads mapped confidently to genome',
												  'fraction', 'percent', '%', 'percentage']):
					formatted_df[col] = formatted_df[col].apply(
						lambda x: f"{float(str(x).replace(',', '.')) * 100:.1f}%".replace('.', ',') 
						if str(x).replace('%', '').replace(',', '.').replace(' ', '').replace('N/A', '').strip() and 
						   str(x).replace('%', '').replace(',', '.').replace(' ', '').replace('N/A', '').strip() != '' and
						   not any(char.isalpha() for char in str(x).replace('%', '').replace('N/A', '')) and
						   x != ""
						else x
					)
	
				# Заменяем точки на запятые в процентных значениях
				if any('%' in str(word) for word in formatted_df[col].to_list() if pd.notna(word)):
					formatted_df[col] = formatted_df[col].apply(lambda x: str(x).replace('.', ',') if pd.notna(x) else x)
	
		# Дополнительная очистка NaN/N/A для всех колонок (на всякий случай)
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
						 total_parts: int = None, archive_type: str = None) -> str:
		"""
		Create email body with statistics table
		"""
		try:
			df = pd.read_csv(statistics_csv_path)
			df.columns	=	[x.replace('_', ' ') for x in df.columns]
			stats_table = self.format_statistics_table(df)
		except Exception as e:
			stats_table = f"<p>Error loading statistics: {e}</p>"
		
		# Add part information if this is a multi-part email
		part_info = ""
		if part_number is not None and total_parts is not None:
			if archive_type == "html":
				part_info = f"<div class='info-box'><p><strong>HTML отчеты - Часть {part_number} из {total_parts}</strong></p></div>"
			elif archive_type == "other":
				part_info = f"<div class='info-box'><p><strong>Дополнительные файлы - Часть {part_number} из {total_parts}</strong></p></div>"
			else:
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
				{stats_table if (part_number == 1 or part_number is None) and archive_type != "other" else ''}
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
				print("✅[Email report] Email sent via SOAP API")
				return True
			except AttributeError:
				try:
					response = self.client.service.SendEmail(**soap_request)
					print("✅[Email report] Email sent via SOAP API")
					return True
				except Exception as e:
					print(f"❌[Email report] Error calling SOAP method SendEmail: {e}")
					return False
					
		except Exception as e:
			print(f"❌[Email report] Error sending via SOAP: {e}")
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
			
			print("✅[Email report] Email sent via SMTP (fallback)")
			return True
			
		except Exception as e:
			print(f"❌[Email report] Error sending via SMTP: {e}")
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
		print(f"❌[Email report] Error loading recipients list: {e}")
		return []

def archive_and_send_report(sum_path: str, flowcell: str, ceph_paths: List[str],
						   config_path: str, sender_email: str, sender_password: str,
						   dry_run: bool = False, max_archive_size_mb: int = 25) -> bool:
	"""
	Main function for archiving and sending report with size limit handling
	"""
	try:
		if not os.path.exists(sum_path):
			print(f"❌[Email report] Directory {sum_path} does not exist")
			return False
		
		stats_csv_path = os.path.join(sum_path, f"{flowcell}_statistics_summary.csv")
		if not os.path.exists(stats_csv_path):
			print(f"❌[Email report] Statistics file not found: {stats_csv_path}")
			return False
		
		# Load configuration
		exchange_config = load_exchange_config(config_path, sender_email, sender_password)
		if not exchange_config:
			print("❌[Email report] Failed to load configuration")
			return False
		
		recipient_emails = load_recipients_config(config_path)
		if not recipient_emails:
			print("❌[Email report] Failed to load recipients list")
			return False
		
		if dry_run:
			print("🔬[Email report] TEST MODE")
			print(f"📁[Email report] Directory: {sum_path}")
			print(f"🔬[Email report] Flowcell: {flowcell}")
			print(f"📧[Email report] Sender: {sender_email}")
			print(f"📧[Email report] Recipients: {recipient_emails}")
			return True
		
		reporter = EmailReporter(exchange_config)
		
		# Step 1: Create single archive first to check total size
		single_archive_name = f"{flowcell}_reports.zip"
		print(f"🕒[Email report] Creating single archive to check size: {single_archive_name}")
		single_archive_path = reporter.create_single_archive(sum_path, single_archive_name)
		
		# Check archive size
		archive_size_mb = os.path.getsize(single_archive_path) / (1024 * 1024)
		print(f"📊[Email report] Total archive size: {archive_size_mb:.1f} MB (limit: {max_archive_size_mb} MB)")
		
		archive_paths = []
		
		if archive_size_mb <= max_archive_size_mb:
			# Single archive is within limit
			print("✅[Email report] Single archive is within size limit")
			archive_paths = [single_archive_path]
			total_parts = 1
			use_category_split = False
		else:
			# Archive is too big, split by category (HTML files separately)
			print("⚠️[Email report] Archive exceeds size limit, splitting HTML files separately...")
			
			# Remove the single archive since we'll create multiple category archives
			os.remove(single_archive_path)
			print("🧹[Email report] Removed oversized single archive")
			
			# Split files by category
			html_file_groups, other_file_groups = reporter.split_files_by_category(sum_path, max_archive_size_mb)
			
			# Create category archives
			archive_paths = reporter.create_category_archives(
				sum_path, flowcell, html_file_groups, other_file_groups
			)
			
			total_parts = len(archive_paths)
			use_category_split = True
		
		print(f"📦[Email report] Found {len(archive_paths)} archive(s) to send")
		
		success_count = 0
		
		for part_number, archive_path in enumerate(archive_paths, 1):
			# Get actual archive size
			part_size_mb = os.path.getsize(archive_path) / (1024 * 1024)
			archive_name = os.path.basename(archive_path)
			print(f"📦[Email report] Processing archive {part_number}/{len(archive_paths)}: {archive_name} ({part_size_mb:.1f} MB)")
			
			# Determine archive type for email subject and body
			archive_type = None
			if use_category_split:
				if "_reports_html" in archive_name:
					archive_type = "html"
				elif "_other_files" in archive_name:
					archive_type = "other"
			
			# Create email body
			print("🕒[Email report] Creating email body...")
			email_body = reporter.create_email_body(
				flowcell, ceph_paths, stats_csv_path, part_number, len(archive_paths), archive_type
			)
			
			# Create subject based on archive type
			if archive_type == "html":
				if len([p for p in archive_paths if "_reports_html" in p]) > 1:
					subject = f"Flowcell {flowcell} - HTML отчеты часть {[p for p in archive_paths if '_reports_html' in p].index(archive_path) + 1} из {len([p for p in archive_paths if '_reports_html' in p])}"
				else:
					subject = f"Flowcell {flowcell} - HTML отчеты"
			elif archive_type == "other":
				if len([p for p in archive_paths if "_other_files" in p]) > 1:
					subject = f"Flowcell {flowcell} - Дополнительные файлы часть {[p for p in archive_paths if '_other_files' in p].index(archive_path) + 1} из {len([p for p in archive_paths if '_other_files' in p])}"
				else:
					subject = f"Flowcell {flowcell} - Дополнительные файлы"
			else:
				if part_number == 1:
					subject = f"Flowcell {flowcell} processing completed - Part {part_number}/{len(archive_paths)}"
				else:
					subject = f"Flowcell {flowcell} processing completed - Part {part_number}/{len(archive_paths)} (Additional Data)"

			print(f"🕒[Email report] Sending email {part_number}/{len(archive_paths)}...")
			
			print("🕒[Email report] Trying SMTP...")
			success = reporter.send_email_smtp_fallback(
				recipient_emails=recipient_emails,
				subject=subject,
				body=email_body,
				attachment_path=archive_path
			)
			
			if success:
				success_count += 1
				print(f"✅[Email report] Successfully sent archive {part_number}/{len(archive_paths)}")
			
			# Clean up temporary archive
			try:
				os.remove(archive_path)
				print(f"🧹[Email report] Cleaned up temporary archive: 2.Results{archive_path.split('2.Results')[-1]}")
			except Exception as e:
				print(f"⚠️[Email report] Warning: Could not clean up archive {archive_path}: {e}")
		
		# Check if all parts were sent successfully
		if success_count == len(archive_paths):
			print(f"✅[Email report] All {len(archive_paths)} email(s) sent successfully!")
			return True
		else:
			print(f"⚠️[Email report] Only {success_count} out of {len(archive_paths)} email(s) were sent successfully")
			return False
			
	except Exception as e:
		print(f"❌[Email report] Critical error: {e}")
		return False
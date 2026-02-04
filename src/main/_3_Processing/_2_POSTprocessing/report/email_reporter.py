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

urllib3.disable_warnings(InsecureRequestWarning)

class EmailReporter:
	def __init__(self, exchange_config: Dict[str, str]):
		self.exchange_config = exchange_config
		self.client = None
		self.session = None
	
	def create_soap_client(self):
		try:
			self.session = Session()
			self.session.auth = HTTPBasicAuth(
				self.exchange_config['sender_email'],
				self.exchange_config['sender_password']
			)
			self.session.verify = False
			settings = Settings(
				strict=False,
				xml_huge_tree=True,
				extra_http_headers={
					'Content-Type': 'text/xml; charset=utf-8',
					'User-Agent': 'Python-SOAP-Client'
				}
			)
			transport = Transport(session=self.session)
			self.client = Client(
				wsdl=self.exchange_config['wsdl_url'],
				settings=settings,
				transport=transport
			)
			print("✅[3.2.r Email report] SOAP client created successfully")
			return True
		except Exception as e:
			print(f"❌[3.2.r Email report] Error creating SOAP client: {e}")
			return False
	
	def get_files_to_archive(self, source_dir: str) -> List[Tuple[str, str, str]]:
		files = []
		for root, _, filenames in os.walk(source_dir):
			for file in filenames:
				if file.endswith(('.html', '.png', '.csv')):
					file_path = os.path.join(root, file)
					relative_path = os.path.relpath(file_path, source_dir)
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
		archive_path = os.path.join(source_dir, archive_name)
		files = self.get_files_to_archive(source_dir)
		with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
			for file_path, relative_path, _ in files:
				zipf.write(file_path, relative_path)
		return archive_path
	
	def split_files_by_category(self, 
								source_dir: str, 
								max_size_mb: int = 25
							   ) -> Tuple[List[List[Tuple[str, str]]], List[List[Tuple[str, str]]]]:
		files = self.get_files_to_archive(source_dir)
		max_size_bytes = max_size_mb * 1024 * 1024
		html_files = [(fp, rp) for fp, rp, ft in files if ft == 'html']
		other_files = [(fp, rp) for fp, rp, ft in files if ft != 'html']
		html_total_size = sum(os.path.getsize(fp) for fp, _ in html_files)
		other_total_size = sum(os.path.getsize(fp) for fp, _ in other_files)
		print(f"📊[3.2.r Email report] HTML files: {len(html_files)} files, {html_total_size / (1024 * 1024):.1f} MB")
		print(f"📊[3.2.r Email report] Other files: {len(other_files)} files, {other_total_size / (1024 * 1024):.1f} MB")
		html_file_groups = self._split_file_group(html_files, max_size_bytes, "HTML")
		other_file_groups = self._split_file_group(other_files, max_size_bytes, "other files")
		return html_file_groups, other_file_groups
	
	def _split_file_group(self, 
						 files: List[Tuple[str, str]], 
						 max_size_bytes: int, 
						 group_name: str
						 ) -> List[List[Tuple[str, str]]]:
		if not files:
			return []
		
		files_with_size = [(fp, rp, os.path.getsize(fp)) for fp, rp in files]
		files_with_size.sort(key=lambda x: x[2], reverse=True)
		
		file_groups = []
		group_sizes = []
		
		for file_path, relative_path, file_size in files_with_size:
			placed = False
			
			for i in range(len(file_groups)):
				if group_sizes[i] + file_size <= max_size_bytes:
					file_groups[i].append((file_path, relative_path))
					group_sizes[i] += file_size
					placed = True
					break
			
			if not placed:
				file_groups.append([(file_path, relative_path)])
				group_sizes.append(file_size)
		
		if len(file_groups) > 1:
			optimized = self._optimize_groups(file_groups, group_sizes, max_size_bytes)
			if optimized:
				file_groups, group_sizes = optimized
		
		print(f"📦[3.2.r Email report] Split {group_name} into {len(file_groups)} part(s)")
		for i, group in enumerate(file_groups):
			group_size = sum(os.path.getsize(fp) for fp, _ in group)
			print(f"📦[3.2.r Email report] Part {i+1}: {len(group)} files, {group_size / (1024 * 1024):.1f} MB")
		
		return file_groups
	
	def _optimize_groups(self, file_groups, group_sizes, max_size_bytes):
		if len(file_groups) < 2:
			return None
		
		min_group_idx = min(range(len(group_sizes)), key=lambda i: group_sizes[i])
		min_group_size = group_sizes[min_group_idx]
		min_group = file_groups[min_group_idx]
		
		moved_files = []
		
		for file_path, relative_path in min_group.copy():
			file_size = os.path.getsize(file_path)
			
			for i in range(len(group_sizes)):
				if i != min_group_idx and group_sizes[i] + file_size <= max_size_bytes:
					file_groups[i].append((file_path, relative_path))
					group_sizes[i] += file_size
					min_group.remove((file_path, relative_path))
					group_sizes[min_group_idx] -= file_size
					moved_files.append((file_path, relative_path))
					break
		
		if not min_group:
			file_groups.pop(min_group_idx)
			group_sizes.pop(min_group_idx)
			return file_groups, group_sizes
		
		return None
	
	def create_category_archives(self, source_dir: str, 
								 base_archive_name: str, 
								 html_file_groups: List[List[Tuple[str, str]]], 
								 other_file_groups: List[List[Tuple[str, str]]]
								) -> List[str]:
		archive_paths = []
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
			print(f"✅[3.2.r Email report] Created HTML archive: {archive_name} ({archive_size:.1f} MB)")
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
			print(f"✅[3.2.r Email report] Created other files archive: {archive_name} ({archive_size:.1f} MB)")
		return archive_paths

	def format_statistics_table(self, df: pd.DataFrame) -> str:
		formatted_df = df.copy()
		formatted_df = formatted_df.rename(columns={'Sample_ID': 'Sample ID'})
		formatted_df = formatted_df.sort_values('Sample ID')
		
		def format_value(x):
			if pd.isna(x):
				return x
			x_str = str(x)
			
			if isinstance(x, str) and '%' in x_str:
				if '.' in x_str and '%' in x_str:
					parts = x_str.split('%')
					if len(parts) > 0:
						number_part = parts[0]
						try:
							number_part = number_part.replace('.', ',')
							return f"{number_part}%"
						except:
							return x_str
			else:
				try:
					num = float(x_str.replace(',', '').replace(' ', ''))
					if num.is_integer():
						return str(int(num))
					else:
						formatted = f"{num:.2f}".replace('.', ',')
						if ',' in formatted:
							formatted = formatted.rstrip('0').rstrip(',')
						return formatted
				except (ValueError, TypeError):
					return x_str
		
		for col in formatted_df.columns[1:]: 
			formatted_df[col] = formatted_df[col].apply(format_value)
		
		html_table = formatted_df.to_html(
			index=False, 
			classes='statistics-table',
			border=1,
			justify='left',
			escape=False,
			na_rep=''
		)
		return html_table

	def create_email_body(self, 
						  flowcell: str, 
						  ceph_paths: List[str], 
						  statistics_csv_path: str, 
						  part_number: int = None, 
						  total_parts: int = None, 
						  archive_type: str = None
						 ) -> str:
		new_text    =   ''
		if flowcell ==  '240607_A00923_0804_BHMKYVDRXY':
			new_text    =   f'В связи с ошибкой обработки CellPlex ячейка {flowcell} обрабатывалась как стандартный scRNA'
		try:
			df = pd.read_csv(statistics_csv_path)
			stats_table = self.format_statistics_table(df)
		except Exception as e:
			stats_table = f"<p>Error loading statistics: {e}</p>"

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

		location_info = f"<p>{ceph_paths}</p>"

		email_body = f"""
		<!DOCTYPE html>
		<html>
		<head>
			<meta charset="UTF-8">
			<meta name="viewport" content="width=device-width, initial-scale=1.0">
			<style>
				body {{ 
					font-family: Arial, sans-serif; 
					margin: 0; 
					padding: 20px; 
					line-height: 1.6; 
					color: #333; 
					word-wrap: break-word;
				}}
				.container {{ 
					max-width: 100%; 
					margin: 0 auto; 
					overflow-x: hidden;
				}}
				.header {{ 
					background-color: #f8f9fa; 
					padding: 20px; 
					border-radius: 5px; 
					margin-bottom: 20px; 
				}}
				.table-container {{
					width: 100%;
					overflow-x: auto;
					margin: 20px 0;
					-webkit-overflow-scrolling: touch;
				}}
				.statistics-table {{ 
					width: 100%;
					min-width: 600px;
					border-collapse: collapse; 
					margin: 0;
					font-size: 14px; 
					table-layout: fixed;
				}}
				.statistics-table th {{ 
					background-color: #e9ecef; 
					padding: 12px; 
					text-align: left; 
					font-weight: bold; 
					border: 1px solid #dee2e6; 
					word-wrap: break-word;
					overflow-wrap: break-word;
				}}
				.statistics-table td {{ 
					padding: 10px; 
					border: 1px solid #dee2e6; 
					word-wrap: break-word;
					overflow-wrap: break-word;
				}}
				.statistics-table tr:nth-child(even) {{ 
					background-color: #f8f9fa; 
				}}
				.statistics-table tr:hover {{ 
					background-color: #e9ecef; 
				}}
				.statistics-table th:first-child,
				.statistics-table td:first-child {{
					width: 20%;
					min-width: 150px;
				}}
				.statistics-table th:nth-child(2),
				.statistics-table td:nth-child(2) {{
					width: 15%;
					min-width: 100px;
				}}
				.statistics-table th:nth-child(3),
				.statistics-table td:nth-child(3) {{
					width: 15%;
					min-width: 100px;
				}}
				.statistics-table th:nth-child(n+4),
				.statistics-table td:nth-child(n+4) {{
					width: calc(50% / (var(--columns-count) - 3));
					min-width: 80px;
				}}
				.info-box {{ 
					background-color: #e7f3ff; 
					border-left: 4px solid #007bff; 
					padding: 15px; 
					margin: 15px 0; 
					border-radius: 3px; 
					word-wrap: break-word;
				}}
				.footer {{ 
					margin-top: 30px; 
					padding-top: 20px; 
					border-top: 1px solid #eee; 
					color: #6c757d; 
					font-size: 12px; 
				}}

				@media screen and (max-width: 768px) {{
					.statistics-table {{
						font-size: 12px;
					}}
					.statistics-table th,
					.statistics-table td {{
						padding: 8px 5px;
					}}
				}}

				@media screen and (max-width: 480px) {{
					body {{
						padding: 10px;
					}}
					.statistics-table {{
						font-size: 11px;
					}}
					.statistics-table th,
					.statistics-table td {{
						padding: 6px 3px;
					}}
				}}
			</style>
		</head>
		<body>
			<div class="container">
				<div class="header"><h2>Автоматический отчет по обработке ячейки {flowcell}</h2></div>
				<p>Добрый день,</p>
				{part_info}
				<div class="info-box">
					<p>{new_text}</p>
					<p>Обработка ячейки <strong>{flowcell}</strong> успешно завершена.</p>
					<p><strong>Расположение данных:</strong><br>
					{location_info}</p>
				</div>
				{(f'<div class="table-container">{stats_table}</div>' 
				  if (part_number == 1 or part_number is None) and archive_type != "other" else '')}
				<div class="footer">
					<p>Это письмо было отправлено автоматически. Пожалуйста, не отвечайте на него.</p>
					<p>Уникальный ключ для фильтрации письма: <strong>=.wni`n;2[KOPr7!</strong></p>
					<p>С уважением,<br>Автоматизированная система обработки данных</p>
				</div>
			</div>
			<script>
				// Динамически вычисляем количество колонок для правильного распределения ширины
				document.addEventListener('DOMContentLoaded', function() {{
					var tables = document.querySelectorAll('.statistics-table');
					tables.forEach(function(table) {{
						var columnCount = table.rows[0].cells.length;
						table.style.setProperty('--columns-count', columnCount);
					}});
				}});
			</script>
		</body>
		</html>
		"""
		return email_body
	
	def send_email_soap(self, 
						recipient_emails: List[str], 
						subject: str, 
						body: str, 
						attachment_path: Optional[str] = None
					   ) -> bool:
		try:
			if not self.client:
				if not self.create_soap_client():
					return False
			attachment_data = None
			attachment_name = None
			if attachment_path and os.path.exists(attachment_path):
				with open(attachment_path, 'rb') as f:
					attachment_data = base64.b64encode(f.read()).decode('utf-8')
				attachment_name = os.path.basename(attachment_path)
			soap_request = {
				'From': {'Address': self.exchange_config['sender_email']},
				'ToRecipients': [{'Mailbox': {'EmailAddress': email}} for email in recipient_emails],
				'Subject': subject,
				'Body': {
					'BodyType': 'HTML',
					'_value_1': body
				}
			}
			if attachment_data:
				soap_request['Attachments'] = {
					'FileAttachment': {
						'Name': attachment_name,
						'Content': attachment_data,
						'ContentType': 'application/zip'
					}
				}
			try:
				response = self.client.service.CreateItem(Message=soap_request)
				print("✅[3.2.r Email report] Email sent via SOAP API")
				return True
			except AttributeError:
				try:
					response = self.client.service.SendEmail(**soap_request)
					print("✅[3.2.r Email report] Email sent via SOAP API")
					return True
				except Exception as e:
					print(f"❌[3.2.r Email report] Error calling SOAP method SendEmail: {e}")
					return False
		except Exception as e:
			print(f"❌[3.2.r Email report] Error sending via SOAP: {e}")
			return False
	
	def send_email_smtp_fallback(self, 
								 recipient_emails: List[str], 
								 subject: str, 
								 body: str, 
								 attachment_path: Optional[str] = None
								) -> bool:
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
			print("✅[3.2.r Email report] Email sent via SMTP (fallback)")
			return True
		except Exception as e:
			print(f"❌[3.2.r Email report] Error sending via SMTP: {e}")
			return False

def load_exchange_config(config_path: str, 
						 sender_email: str, 
						 sender_password: str
						) -> Dict[str, str]:
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
		print(f"❌[3.2.r Email report]  Error loading configuration: {e}")
		return {}

def load_recipients_config(config_path: str
						  ) -> List[str]:
	config = configparser.ConfigParser()
	try:
		config.read(config_path)
		if 'RECIPIENTS' not in config:
			raise ValueError("[RECIPIENTS] section not found")
		emails_str = config['RECIPIENTS'].get('emails', '')
		emails = [email.strip() for email in emails_str.split(',') if email.strip()]
		return emails
	except Exception as e:
		print(f"❌[3.2.r Email report] Error loading recipients list: {e}")
		return []

def archive_and_send_report(flowcell_sample_processed: dict, 
                          sender_email:str,
                          sender_password:str,
                          config_path:str,
                          max_archive_size_mb: int = 25) -> bool:
  
  all_results = []
  
  try:
    seqtypes_set = list({value.get('SeqType') for value in flowcell_sample_processed.values() if value.get('SeqType')})
    
    for seq_type_keys in seqtypes_set:
      print(f"📊[3.2.r Email report] Processing SeqType: {seq_type_keys}")
      filtered_data = {key: value for key, value in flowcell_sample_processed.items() if value.get('SeqType') == seq_type_keys}
      first_key = list(filtered_data.keys())[0]
      sum_path = filtered_data[first_key]['Path local sum stat']
      flowcell = filtered_data[first_key]['Flowcell']
      ceph_paths = filtered_data[first_key]['Path ceph results']
      sender_email = sender_email
      sender_password = sender_password

      if not os.path.exists(sum_path):
        print(f"❌[3.2.r Email report] Directory {sum_path} does not exist")
        all_results.append(False)
        continue  # Продолжаем со следующим SeqType

      stats_csv_path = os.path.join(sum_path, f"{flowcell}_stat.csv")
      if not os.path.exists(stats_csv_path):
        print(f"❌[3.2.r Email report] Statistics file not found: {stats_csv_path}")
        all_results.append(False)
        continue

      exchange_config = load_exchange_config(config_path=config_path, 
                                            sender_email=sender_email, 
                                            sender_password=sender_password)
      if not exchange_config:
        print("❌[3.2.r Email report] Failed to load configuration")
        all_results.append(False)
        continue

      recipient_emails = load_recipients_config(config_path=config_path)
      if not recipient_emails:
        print("❌[3.2.r Email report] Failed to load recipients list")
        all_results.append(False)
        continue

      reporter = EmailReporter(exchange_config)
      single_archive_name = f"{flowcell}_reports.zip"
      print(f"🕒[3.2.r Email report] Creating single archive to check size: {single_archive_name}")
      single_archive_path = reporter.create_single_archive(sum_path, single_archive_name)
      archive_size_mb = os.path.getsize(single_archive_path) / (1024 * 1024)
      print(f"📊[3.2.r Email report] Total archive size: {archive_size_mb:.1f} MB (limit: {max_archive_size_mb} MB)")
      
      archive_paths = []
      if archive_size_mb <= max_archive_size_mb:
        print("✅[3.2.r Email report] Single archive is within size limit")
        archive_paths 		= [single_archive_path]
        total_parts 		= 1
        use_category_split 	= False
      else:
        print("⚠️[3.2.r Email report] Archive exceeds size limit, splitting HTML files separately...")
        os.remove(single_archive_path)
        print("🧹[3.2.r Email report] Removed oversized single archive")
        html_file_groups, other_file_groups = reporter.split_files_by_category(sum_path, max_archive_size_mb)
        archive_paths = reporter.create_category_archives(
          sum_path, flowcell, html_file_groups, other_file_groups
        )
        total_parts = len(archive_paths)
        use_category_split = True

      print(f"📦[3.2.r Email report] Found {len(archive_paths)} archive(s) to send")
      success_count = 0
      
      for part_number, archive_path in enumerate(archive_paths, 1):
        part_size_mb = os.path.getsize(archive_path) / (1024 * 1024)
        archive_name = os.path.basename(archive_path)
        print(f"📦[3.2.r Email report] Processing archive {part_number}/{len(archive_paths)}: {archive_name} ({part_size_mb:.1f} MB)")
        
        archive_type = None
        if use_category_split:
          if "_reports_html" in archive_name:
            archive_type = "html"
          elif "_other_files" in archive_name:
            archive_type = "other"
        
        print("🕒[3.2.r Email report] Creating email body...")
        email_body = reporter.create_email_body(
          flowcell, ceph_paths, stats_csv_path, part_number, len(archive_paths), archive_type)
        
        if archive_type == "html":
          html_archives = [p for p in archive_paths if "_reports_html" in os.path.basename(p)]
          if len(html_archives) > 1:
            subject = f"Flowcell {flowcell} - HTML отчеты часть {html_archives.index(archive_path) + 1} из {len(html_archives)}"
          else:
            subject = f"Flowcell {flowcell} - HTML отчеты"
        elif archive_type == "other":
          other_archives = [p for p in archive_paths if "_other_files" in os.path.basename(p)]
          if len(other_archives) > 1:
            subject = f"Flowcell {flowcell} - Дополнительные файлы часть {other_archives.index(archive_path) + 1} из {len(other_archives)}"
          else:
            subject = f"Flowcell {flowcell} - Дополнительные файлы"
        else:
          if part_number == 1:
            subject = f"Flowcell {flowcell} processing completed - Part {part_number}/{len(archive_paths)}"
          else:
            subject = f"Flowcell {flowcell} processing completed - Part {part_number}/{len(archive_paths)} (Additional Data)"

        print(f"🕒[3.2.r Email report] Sending email {part_number}/{len(archive_paths)}...")
        print("🕒[3.2.r Email report] Trying SMTP...")
        success = reporter.send_email_smtp_fallback(
          recipient_emails=recipient_emails,
          subject=subject,
          body=email_body,
          attachment_path=archive_path
        )
        
        if success:
          success_count += 1
          print(f"✅[3.2.r Email report] Successfully sent archive {part_number}/{len(archive_paths)}")
        
        try:
          os.remove(archive_path)
          print(f"🧹[3.2.r Email report] Cleaned up temporary archive: 2.Results{archive_path.split('2.Results')[-1]}")
        except Exception as e:
          print(f"⚠️[3.2.r Email report] Warning: Could not clean up archive {archive_path}: {e}")
      
      if success_count == len(archive_paths):
        print(f"✅[3.2.r Email report] All {len(archive_paths)} email(s) for SeqType {seq_type_keys} sent successfully!")
        all_results.append(True)
      else:
        print(f"⚠️[3.2.r Email report] Only {success_count} out of {len(archive_paths)} email(s) for SeqType {seq_type_keys} were sent successfully")
        all_results.append(False)
    
    if all_results:
      overall_success = all(all_results)
      print(f"📊[3.2.r Email report] Overall result: {'SUCCESS' if overall_success else 'FAILURE'}")
      print(f"📊[3.2.r Email report] Individual results: {all_results}")
      return overall_success
    else:
      print("❌[3.2.r Email report] No SeqTypes processed")
      return False

  except Exception as e:
    print(f"❌[3.2.r Email report] Unexpected error: {e}")
    return False
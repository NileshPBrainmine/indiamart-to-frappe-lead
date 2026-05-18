import logging
import logging.handlers
import os
import shutil
from datetime import date, datetime, timedelta


BASE_LOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/logs'
KEEP_DAYS = 7


class DailyFolderRotatingHandler(logging.handlers.BaseRotatingHandler):
    """
    Writes to logs/YYYY-MM-DD/app.log.
    Rotates at midnight into a new date folder and purges folders older than KEEP_DAYS.
    """

    def __init__(self, base_dir, keep_days=KEEP_DAYS, encoding='utf-8'):
        self.base_dir = base_dir
        self.keep_days = keep_days
        self._current_date = date.today()
        log_path = self._log_path(self._current_date)
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        super().__init__(log_path, mode='a', encoding=encoding)
        self._purge_old_folders()  # clean up on startup

    def _log_path(self, d):
        return os.path.join(self.base_dir, d.strftime('%Y-%m-%d'), 'app.log')

    def shouldRollover(self, record):
        return date.today() > self._current_date

    def doRollover(self):
        if self.stream:
            self.stream.close()
            self.stream = None

        self._current_date = date.today()
        new_path = self._log_path(self._current_date)
        os.makedirs(os.path.dirname(new_path), exist_ok=True)
        self.baseFilename = os.path.abspath(new_path)
        self.stream = self._open()
        self._purge_old_folders()

    def _purge_old_folders(self):
        cutoff = date.today() - timedelta(days=self.keep_days)
        for entry in os.scandir(self.base_dir):
            if not entry.is_dir():
                continue
            try:
                folder_date = datetime.strptime(entry.name, '%Y-%m-%d').date()
                if folder_date < cutoff:
                    shutil.rmtree(entry.path)
                    logging.getLogger(__name__).info(
                        f"Removed old log folder: {entry.name}"
                    )
            except ValueError:
                pass  # skip non-date folders (e.g. seen_leads.json lives here too)


os.makedirs(BASE_LOG_DIR, exist_ok=True)

file_handler = DailyFolderRotatingHandler(BASE_LOG_DIR)
file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))

console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))

logging.basicConfig(level=logging.INFO, handlers=[file_handler, console_handler])

logger = logging.getLogger(__name__)

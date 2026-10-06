#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Oct 4 11:32 2023

@author: jasonpbu
"""

from pathlib import Path
from subprocess import PIPE, STDOUT, Popen
from threading import Lock, Thread

_FLOW_OUTPUT_LOCK = Lock()
_FLOW_CATEGORIES = ('import_mcc', 'export_mcc', 'export_dcc')
_FLOW_ARCHIVE_CATEGORIES = _FLOW_CATEGORIES + ('level_1', 'level_2')


def _flow_log_version(path):
    """Identify a log written by this run, without replaying an older result."""
    try:
        stat = path.stat()
        return stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns
    except OSError:
        return None

class UiFlow(object):

    operation_user_flag = False
    operation_host_flag = False
    operation_password_flag = False
    archiving_user_flag = False
    archiving_host_flag = False
    archiving_password_flag = False
    
    def __init__(self):
        pass
    
    ### flow_link_interface ###

    def flow_operation_user(self):

        self.operation_user = self.ui.flow_operation_user_line.text()

        if len(self.operation_user) == 0:
            self.operation_user_flag = False
        else:
            self.operation_user_flag = True
        
        self.flow_socc_operation_processing()

    def flow_operation_host(self):

        self.operation_host = self.ui.flow_operation_host_line.text()

        if len(self.operation_host) == 0:
            self.operation_host_flag = False
        else:
            self.operation_host_flag = True
        
        self.flow_socc_operation_processing()

    def flow_operation_password(self):

        self.operation_password = self.ui.flow_operation_password_line.text()

        if len(self.operation_password) == 0:
            self.operation_password_flag = False
        else:
            self.operation_password_flag = True
        
        self.flow_socc_operation_processing()        

    def flow_socc_operation_processing(self):

        if self.operation_user_flag and self.operation_host_flag and self.operation_password_flag:
            self.ui.flow_socc_operation_group.setEnabled(True)
            self.ui.flow_operation_processing_group.setEnabled(True)
        else:
            self.ui.flow_socc_operation_group.setEnabled(False)
            self.ui.flow_operation_processing_group.setEnabled(False)
    
    def flow_archiving_user(self):

        self.archiving_user = self.ui.flow_archiving_user_line.text()

        if len(self.archiving_user) == 0:
            self.archiving_user_flag = False
        else:
            self.archiving_user_flag = True
        
        self.flow_processing_archiving()

    def flow_archiving_host(self):

        self.archiving_host = self.ui.flow_archiving_host_line.text()

        if len(self.archiving_host) == 0:
            self.archiving_host_flag = False
        else:
            self.archiving_host_flag = True
        
        self.flow_processing_archiving()

    def flow_archiving_password(self):

        self.archiving_password = self.ui.flow_archiving_password_line.text()

        if len(self.archiving_password) == 0:
            self.archiving_password_flag = False
        else:
            self.archiving_password_flag = True
        
        self.flow_processing_archiving()        

    def flow_processing_archiving(self):

        if self.archiving_user_flag and self.archiving_host_flag and self.archiving_password_flag:
            self.ui.flow_processing_archiving_group.setEnabled(True)
        else:
            self.ui.flow_processing_archiving_group.setEnabled(False)
    
    ### flow_link_interface_end ###

    ### flow_run ###

    def _flow_run(self, script, action, log_names, credentials=()):
        """Run asynchronously, then print the script output and refreshed logs."""
        password = credentials[2] if credentials else ''

        def report(message):
            if password:
                message = message.replace(password, '***')
            with _FLOW_OUTPUT_LOCK:
                print(message, flush=True)

        # Repeated clicks must not mix two runs writing the same log files.
        with _FLOW_OUTPUT_LOCK:
            if not hasattr(self, '_flow_active_scripts'):
                self._flow_active_scripts = set()
            already_running = script in self._flow_active_scripts
            if not already_running:
                self._flow_active_scripts.add(script)
        if already_running:
            report(f'[Flow] Already running: {action}')
            return

        log_paths = [(Path('../level_0/log') / name).resolve() for name in log_names]
        before = {path: _flow_log_version(path) for path in log_paths}
        report(f'\n[Flow] START: {action}' + (
            f' | Server: {credentials[0]}@{credentials[1]}' if credentials else ''
        ))

        def run_and_report():
            try:
                # Drain both streams in the worker so the GUI stays responsive.
                process = Popen(
                    [script, *credentials], stdout=PIPE, stderr=STDOUT,
                    encoding='utf-8', errors='replace',
                )
                output, _ = process.communicate()
                lines = [f'\n[Flow] RESULT: {action} | Script exit code: {process.returncode}']
                if output.strip():
                    lines.extend(('[Flow] Script output:', output.rstrip()))
                for path in log_paths:
                    lines.append(f'[Flow] Log: {path}')
                    version = _flow_log_version(path)
                    if version is None:
                        lines.append('  Log unavailable; this result could not be confirmed.')
                    elif version == before[path]:
                        lines.append('  Log was not updated; no new result could be confirmed.')
                    else:
                        try:
                            content = path.read_text(encoding='utf-8', errors='replace').strip()
                        except OSError as error:
                            lines.append(f'  Could not read log: {error}')
                        else:
                            lines.append(content or '  No entries recorded (empty log).')
                # Scripts can exit zero even when an individual SFTP command fails;
                # show the actual transcript instead of claiming transfer success.
                lines.append(f'[Flow] END: {action}')
                report('\n'.join(lines))
            except OSError as error:
                report(f'[Flow] FAILED: {action} | {error}')
            finally:
                with _FLOW_OUTPUT_LOCK:
                    self._flow_active_scripts.discard(script)

        worker = Thread(target=run_and_report, daemon=True)
        worker.start()
        return worker

    def _flow_operation_run(self, script, action, log_names):
        return self._flow_run(script, action, log_names, (
            self.operation_user, self.operation_host, self.operation_password,
        ))

    def flow_socc_operation_update_socc(self):
        return self._flow_operation_run(
            './run_get_socc_log.sh', 'Update SOCC file lists (via Operation server)',
            [f'from_operation/socc_{category}.log' for category in _FLOW_CATEGORIES],
        )

    def flow_socc_operation_update_operation(self):
        return self._flow_operation_run(
            './run_get_operation_log.sh', 'Update Operation server file lists (SOCC link)',
            [f'from_operation/operation_{category}.log' for category in _FLOW_CATEGORIES],
        )

    def flow_socc_operation_clone(self):
        return self._flow_operation_run(
            './run_download_from_socc.sh', 'Clone / Download: SOCC -> Operation server',
            [f'from_operation/{category}_download_from_socc.log' for category in _FLOW_CATEGORIES],
        )

    def flow_socc_operation_push(self):
        return self._flow_operation_run(
            './run_upload_to_socc.sh', 'Push / Upload: Operation server -> SOCC',
            ['from_operation/import_mcc_upload_to_socc.log'],
        )

    def flow_operation_processing_update_operation(self):
        return self._flow_operation_run(
            './get_operation_log.sh', 'Update Operation server file lists (Processing link)',
            [f'operation_{category}.log' for category in _FLOW_CATEGORIES],
        )

    def flow_operation_processing_update_processing(self):
        return self._flow_run(
            './get_processing_log.sh', 'Update Processing (local) file lists',
            [f'processing_{category}.log' for category in _FLOW_CATEGORIES],
        )

    def flow_operation_processing_clone(self):
        return self._flow_operation_run(
            './download_from_operation.sh', 'Clone / Download: Operation server -> Processing (local)',
            [f'{category}_download_from_operation.log' for category in _FLOW_CATEGORIES],
        )

    def flow_operation_processing_push(self):
        return self._flow_operation_run(
            './upload_to_operation.sh', 'Push / Upload: Processing (local) -> Operation server',
            ['import_mcc_upload_to_operation.log'],
        )

    def flow_processing_archiving_update_processing(self):
        return self._flow_run(
            './archive_get_all_processing_log.sh', 'Update Processing (local) file lists (Archiving link)',
            [f'to_archiving/processing_{category}.log' for category in _FLOW_ARCHIVE_CATEGORIES],
        )

    def flow_processing_archiving_update_archiving(self):
        return self._flow_run(
            './archive_get_all_archiving_log.sh', 'Update Archiving server file lists',
            [f'to_archiving/archiving_{category}.log' for category in _FLOW_ARCHIVE_CATEGORIES],
            (self.archiving_user, self.archiving_host, self.archiving_password),
        )

    def flow_processing_archiving_push(self):
        return self._flow_run(
            './archive_upload_to_archiving.sh', 'Push / Upload: Processing (local) -> Archiving server',
            [f'to_archiving/{category}_upload_to_archiving.log' for category in _FLOW_ARCHIVE_CATEGORIES],
            (self.archiving_user, self.archiving_host, self.archiving_password),
        )


    ### flow_run_end ###

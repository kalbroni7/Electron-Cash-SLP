import json
import requests
import base64
import threading

from electroncash.slp_graph_search import slp_gs_mgr
from .util import PrintError

# TODO https://explorer.bitcoinverde.org/api/v1/slp/validate/
class VerdeValidationJob(PrintError):
    def __init__(self, txid, number_of_validations_needed, callback):
        self.txid = txid
        self.number_of_validations_needed = number_of_validations_needed
        self.callback = callback
        self.validity = 0

    def _query_server(self, server):
        try:
            url = f"{server}/api/v1/slp/validate/{self.txid}"
            result = requests.get(url=url, timeout=30)
            result_json = result.json()
        except Exception as e:
            self.print_error(e)
            raise (Exception("Server was not reachable or something went wrong."))

        if "isValid" in result_json.keys() and result_json['isValid']:
            return True
        return False

    def validate(self):
        verde_servers = slp_gs_mgr.verde_host
        valid_counter = 0
        for server in verde_servers:
            try:
                result = self._query_server(server)
                if result:
                    self.print_error(server, self.txid, result)
                    valid_counter += 1
                    if valid_counter >= self.number_of_validations_needed:
                        break
            except Exception as e:
                self.print_exception(e)
                continue

        if valid_counter >= self.number_of_validations_needed:
            self.validity = 1
        else:
            self.validity = 2
        self.callback(self)


class VerdeValidationJobManager(PrintError):
    def __init__(self, thread_name="VerdeValidation"):
        self.jobs_list = list()

        self.run_validation = threading.Event()
        self.thread = threading.Thread(target=self.mainloop, name=thread_name, daemon=True)
        self.thread.start()

    def _pause_mainloop(self):
        self.run_validation.clear()

    def _resume_mainloop(self):
        self.run_validation.set()

    def add_job(self, verde_validation_job):
        self.jobs_list.append(verde_validation_job)
        self._resume_mainloop()

    def mainloop(self):
        while True:
            self.run_validation.wait()
            if self.jobs_list:
                job = self.jobs_list.pop()
                job.validate()
            else:
                self._pause_mainloop()

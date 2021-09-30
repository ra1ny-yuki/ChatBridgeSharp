from threading import Thread, current_thread, RLock
from typing import NamedTuple, Callable, List, Optional

from chatbridge.common.logger import ChatBridgeLogger
from chatbridge.core.network.cryptor import AESCryptor


class Address(NamedTuple):
	hostname: str
	port: int

	def __str__(self):
		return '{}:{}'.format(self.hostname, self.port)


class ChatBridgeBase:
	def __init__(self, name: str, aes_key: str):
		super().__init__()
		self.__name = name
		self.logger = ChatBridgeLogger(self.get_logging_name(), file_name=self.get_logging_file_name())
		self.aes_key = aes_key
		self._cryptor = AESCryptor(aes_key)
		self.__thread_run: Optional[Thread] = None
		self.__threads: List[Thread] = []
		self.__threads_lock = RLock()

	def get_name(self) -> str:
		return self.__name

	def get_logging_name(self) -> str:
		return self.get_name()

	def get_logging_file_name(self) -> Optional[str]:
		"""
		None for no file handler
		"""
		return type(self).__name__

	def _start_thread(self, target: Callable, name: str) -> Thread:
		thread = Thread(target=target, args=(), name=name, daemon=True)
		thread.start()
		self.__threads.append(thread)
		return thread

	@classmethod
	def _get_main_loop_thread_name(cls):
		return 'MainLoop'

	def start(self):
		def func():
			self._main_loop()
			self.__clean_up()

		with self.__threads_lock:
			if self.__thread_run is not None:
				raise RuntimeError('Already running')
			self.__thread_run = self._start_thread(func, self._get_main_loop_thread_name())

	def stop(self):
		"""
		Stop the client/server, and wait until the MainLoop thread exits
		Need to be called on a non-MainLoop thread
		"""
		self.__join_threads()

	def _main_loop(self):
		pass

	def __clean_up(self):
		self.logger.close_file()
		self.__thread_run = None

	def __join_threads(self):
		self.logger.debug('Joining threads {}'.format(self.__threads))
		with self.__threads_lock:
			for thread in self.__threads:
				if thread is not current_thread():
					thread.join()
				else:
					self.logger.warning('Joining current thread {}'.format(thread))
			self.__threads.clear()
			self.__thread_run = None
		self.logger.debug('Joined threads')

	def _on_external_thread(self):
		return current_thread() not in self.__threads

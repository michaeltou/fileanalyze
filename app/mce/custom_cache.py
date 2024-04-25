import time
from threading import RLock
from collections import OrderedDict


class LRUTTLCache:
    def __init__(self, lru_maxsize=128, ttl_seconds=60 * 60):
        self.__lru_maxsize = lru_maxsize
        self.__ttl_seconds = ttl_seconds
        self.__cache = OrderedDict()
        self.__lock = RLock()

        # with _check_lock:
        #     _cache_list.append(self)

    def timeout_check(self):
        with self.__lock:
            for key in list(self.__cache.keys()):
                timestamp = self.__cache[key][1]
                if time.time() - timestamp > self.__ttl_seconds:
                    del self.__cache[key]

    def get(self, key):
        with self.__lock:
            if key in self.__cache:
                value, timestamp = self.__cache[key]
                if time.time() - timestamp > self.__ttl_seconds:
                    del self.__cache[key]
                else:
                    self.__cache.move_to_end(key)
                    return value
        return None

    def put(self, key, value):
        if key is not None and value is not None:
            with self.__lock:
                if len(self.__cache) >= self.__lru_maxsize:
                    self.__cache.popitem(last=False)
                self.__cache[key] = (value, time.time())

    def delete(self, key):
        with self.__lock:
            if key in self.__cache:
                del self.__cache[key]

    def clear(self):
        with self.__lock:
            self.__cache.clear()

    def view(self, key):
        with self.__lock:
            if key in self.__cache:
                return self.__cache[key]
        return None

    def keys(self):
        with self.__lock:
            return list(self.__cache.keys())

    @property
    def size(self):
        with self.__lock:
            return len(self.__cache)

    @property
    def lru_maxsize(self):
        return self.__lru_maxsize

    @property
    def ttl_seconds(self):
        return self.__ttl_seconds

    @property
    def lock(self):
        return self.__lock


# _cache_list = []
# _check_interval = 60 * 10
# _check_lock = RLock()
#
#
# def _check():
#     while True:
#         time.sleep(_check_interval)
#         with _check_lock:
#             for cache in _cache_list:
#                 cache.timeout_check()
#
#
# _check_thread = Thread(target=_check)
# _check_thread.daemon = True
# _check_thread.start()

from secrets import randbelow
from io import BytesIO


class bytestr(bytearray):
    """Mutable replacement for str"""

    BYTESTR_ONLY_KWARGS = (
        ("randomize_on_destroy", False),
        ("clearmem_on_destroy", True),
        ("clearmem_on_stream", True),
        ("placeholder_char", "?"),
        ("verbosity", 0),
        ("with_context", False)
    )

####STATIC METHODS####
    @staticmethod
    def destroy(byteslike_obj, clearmem=True, randomize=False):
        if hasattr(byteslike_obj, "clear"):
            if randomize:
                bytestr.set_all(byteslike_obj, randbelow, 256)
            if clearmem or type(byteslike_obj) is bytearray:
                bytestr.set_all(byteslike_obj, 0)
            byteslike_obj.clear()
        del byteslike_obj

    @staticmethod
    def set_all(byteslike_obj, int_func, *args, set_by_index=False):
        for i in range(len(byteslike_obj)):
            if set_by_index:
                byteslike_obj[i] = int_func(i, *args)
            else:
                byteslike_obj[i] = int_func(*args) if args else int_func

    @staticmethod
    def parse_arg(arg, valid_types=(bytes,)):
        # Returns generator of ints or bytes-like object as needed
        if isinstance(arg, int) and int in valid_types:
            if arg > 255:
                # Handle large ints as strings of digits
                return (ord(char) for char in str(arg))
            return (arg,)

        if isinstance(arg, (bytes, bytearray, memoryview)):
            if int in valid_types:
                return (_int for _int in arg)
            return bytestr(arg)

        if isinstance(arg, str):
            if int in valid_types:
                return (ord(char) for char in arg)
            return bytestr(arg)

        elif arg is not None:
            print("Failed to parse ", arg)
            raise TypeError


####SPECIAL METHODS####


    def __init__(self, *args, **kwargs):
        if args and isinstance(args[0], str) and "encoding" not in kwargs:
            kwargs["encoding"] = "utf-8"

        self.__dict__.update({kwarg[0]: kwargs.pop(*kwarg)
                              for kwarg in self.BYTESTR_ONLY_KWARGS})
        super().__init__(*args, **kwargs)
        self.cursor = len(self)

        for arg in args:
            self.destroy(arg)

        # if self.with_context:
        self.context = []

    def __del__(self):
        self.destroy(self)
        del self

    def __str__(self):
        return "".join(chr(_int) for _int in self)

    def __add__(self, other):
        return self.__iadd__(other)

    def __iadd__(self, other):
        self.extend(other)
        self.destroy(other)
        return self

    def __radd__(self, other):
        self.insert(0, other)
        self.destroy(other)
        return self

    def __isub__(self, other):
        for i in range(len(other)):
            self[len(self) - len(other) + i] = 0
            del self[len(self) - len(other) + i]
        self.destroy(other)
        return self

    def __sub__(self, other):
        return self.__isub__(other)

    def __imul__(self, n):
        before = self.copy()
        for _ in range(n):
            self.extend(before)
        del before
        return self

    def __mul__(self, n):
        return bytestr(self).__imul__(n)

    def __enter__(self):
        bytestr.__init__(self, with_context=True)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.destroy(self)
        for item in self.context:
            self.destroy(item)

    def __contains__(self, item):
        return super().__contains__(bytestr.parse_arg(item))

####MUTABLE SEQUENCE METHODS####

    def insert(self, index, item):
        for i, _int in enumerate(bytestr.parse_arg(item, valid_types=(int,))):
            super().insert(index + i, _int)

    def append(self, item):
        for _int in bytestr.parse_arg(item, valid_types=(int,)):
            super().append(_int)

    def extend(self, seq):
        for item in seq:
            self.append(item)

    def copy(self):
        kwargs = {kwarg[0]: self.__dict__.get(kwarg)
                  for kwarg in self.BYTESTR_ONLY_KWARGS}
        return bytestr(self[:], **kwargs)

####SUPER METHODS####
    def count(self, sub, start=None, end=None):
        return super().count(self.parse_arg(sub), start, end)

    def find(self, sub, start=None, end=None):
        return super().find(self.parse_arg(sub), start, end)

    def rfind(self, sub, start=None, end=None):
        return super().rfind(self.parse_arg(sub), start, end)

    def index(self, sub, start=None, end=None):
        return super().index(self.parse_arg(sub), start, end)

    def rindex(self, sub, start=None, end=None):
        return super().rindex(self.parse_arg(sub), start, end)

    def startswith(self, sub, start=None, end=None):
        return super().startswith(self.parse_arg(sub), start, end)

    def endswith(self, sub, start=None, end=None):
        return super().endswith(self.parse_arg(sub), start, end)

###CONTEXT DEPENDANT METHODS####
    def return_with_context(self, *args):
        arg_lst = list(*args)
        if self.with_context:
            self.context.extend(arg_lst)
        return arg_lst

    def split(self, sep=None, maxsplit=-1):
        return self.return_with_context(bytestr(byteslike_obj) for byteslike_obj in super().split(self.parse_arg(sep), maxsplit))

    def rsplit(self, sep=None, maxsplit=-1):
        return self.return_with_context(bytestr(byteslike_obj) for byteslike_obj in super().rsplit(self.parse_arg(sep), maxsplit))

    def partition(self, sep):
        return self.return_with_context(bytestr(byteslike_obj) for byteslike_obj in super().partition(self.parse_arg(sep)))

    def rpartition(self, sep):
        return self.return_with_context(bytestr(byteslike_obj) for byteslike_obj in super().rpartition(self.parse_arg(sep)))


####OVERRIDDES FOR BYTEARRAY METHODS THAT DO NOT OPERATE IN PLACE####
# From: https://docs.python.org/3/library/stdtypes.html#bytearray.replace
# "The bytearray version of this method does not operate in place
# it always produces a new object, even if no changes were made."

    def replace(self, old, new, count=None):
        max_count = count if count and count < len(self) else self.count(old)
        actual_count = 0

        sub_index = self.find(old)
        while sub_index >= 0 and actual_count < max_count:
            del self[sub_index:sub_index+len(old)]
            self.insert(sub_index, new)
            sub_index = self.find(old)
            actual_count += 1
        return self

    def center(self, width, fill=" "):
        while len(self) <= width:
            self.insert(0, fill)
            if len(self) <= width:
                self.append(fill)
        return self

    def ljust(self, width, fill=" "):
        while len(self) <= width:
            self.append(fill)
        return self

    def lstrip(self, *chars):
        return self.strip(*chars, right=False)

    def rjust(self, width, fill=" "):
        while len(self) <= width:
            self.insert(0, fill)
        return self

    def rstrip(self, *chars):
        return self.strip(*chars, left=False)

    def strip(self, chars="\n\t ", left=True, right=True):
        chars = tuple(ord(char) for char in chars)
        if left:
            lbound = 0
            for i in self.range():
                if self[i] in chars:
                    self[i] = 0
                    lbound = i + 1
                    continue
                break
            del self[:lbound]
        if right:
            rbound = -1
            for i in self.range(1, 1):
                if self[-i] in chars:
                    self[-i] = 0
                    rbound = -i
                    continue
                break
            del self[rbound:]
        return self

    def capitalize(self):
        if len(self) > 0:
            self[0] = ord(chr(self[0]).upper())
        return self

    def expandtabs(self, tabsize=8, tabchar="\t", fill=" "):
        return self.replace(tabchar, tabsize*fill)

    def lower(self):
        self.set_all(self, lambda i: ord(
            chr(self[i]).lower()), set_by_index=True)
        return self

    def upper(self):
        self.set_all(self, lambda i: ord(
            chr(self[i]).upper()), set_by_index=True)
        return self

    def swapcase(self):
        self.set_all(self, lambda i: ord(
            chr(self[i]).swapcase()), set_by_index=True)
        return self

    def title(self, space_char=" "):
        self.capitalize()
        for i in self.range(1):
            if self[i - 1] == ord(space_char):
                self[i] = ord(chr(self[i]).upper())
        return self

    def zfill(self, width):
        i = 0
        if self[0] in (ord("-"), ord("+")):
            i += 1
        while i < len(self):
            if len(self) < width:
                self.insert(i, ord(b"0"))
            i += 1
        return self

####OVERRIDDEN BYTEARRAY METHODS TO REPLACE STR METHODS####
    def join(self, seq):
        sep = self.copy()
        if seq:
            self.insert(0, seq[0])
            for item in seq[1:]:
                self.extend((item, sep))
        self.destroy(sep)
        return self

    def format(self, *args):
        for arg in args:
            self.replace(b"{}", arg, count=1)
        return self

####CUSTOM METHODS####
    def range(self, start=0, stop=0):
        yield from range(start, len(self)+stop)

    def _destroy(self, byteslike_obj):
        self.destroy(byteslike_obj, clearmem=self.clearmem_on_destroy,
                     randomize=self.randomize_on_destroy)

    def clearmem(self):
        self.set_all(self, 0)
        self.clear()
        self.seek(0)

    def randomize(self):
        self.set_all(self, randbelow, 256)

    def seek(self, position):
        self.cursor = max(0, position - 1)

    @property
    def placeholder(self):
        return ("".join(self.placeholder_char for _ in range(self.cursor)), self.cursor)

    def write(self, string):
        self.seek(0)
        for char in string:
            if not char is self.placeholder_char:
                if self.cursor >= len(self):
                    self.append(ord(char))
                elif not self[self.cursor] is 0:
                    self.insert(self.cursor, char)
            self.cursor += 1

    def backspace(self):
        if self.cursor >= 0 and self.cursor < len(self) - 1:
            for i in range(self.cursor, len(self) - 1):
                self[i] = self[i + 1]
        if len(self) > 0:
            self[-1] = 0
            del self[-1]

    def streaminto(self, fn, format_fn=chr):
        for i in self.range():
            fn(format_fn(self[i]))
        if self.clearmem_on_stream:
            self.clearmem()

    def putinto(self, queue, format_fn=chr):
        self.streaminto(queue.put, format_fn)

    def readinto(self, writeable_obj, format_fn=chr):
        self.streaminto(writeable_obj.write, format_fn)

    class BytestrIO(BytesIO):
        def read(self, size=-1):
            pos = self.tell()
            data = super().read(size)
            self.seek(pos)
            for _ in range(max(size, len(self.getvalue()))):
                self.write(b"0")
            return data

    @property
    def IO(self):
        self.context.append(self.BytestrIO(self))
        self.clearmem()
        return self.context[-1]

    def print_data(self):
        print(self)
        print(self[:])
        print(len(self))
        print(id(self))

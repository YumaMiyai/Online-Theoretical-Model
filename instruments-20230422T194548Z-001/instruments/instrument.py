class Instrument:
    _range: (float, float)

    def __init__(self, *args, **kwargs):
        if 'range' in kwargs:
            self._range = kwargs['range']
        else:
            self._range = None

    @property
    def normal_operating_range(self):
        return self._range

    @normal_operating_range.setter
    def normal_operating_range(self, value):
        self._range = value

    @property
    def within_range(self) -> bool:
        if self._range is not None:
            if self.value < self._range[0] or self.value > self._range[1]:
                return False
            return True
        else:
            return True

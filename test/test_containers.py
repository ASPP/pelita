import pytest

from pelita.containers import *


class TestMesh:
    def test_init(self):
        m = Mesh(2, 2)
        assert list(m.values()) == [None, None, None, None]
        assert m.shape == (2, 2)
        m = Mesh(0, 0)
        assert list(m.values()) == []
        assert m.shape == (0, 0)
        m = Mesh(1, 4)
        assert list(m.values()) == [None, None, None, None]
        assert m.shape == (1, 4)
        m = Mesh(4, 1)
        assert list(m.values()) == [None, None, None, None]
        assert m.shape == (4, 1)

    def test_indices(self):
        m = Mesh(2, 3)
        target = [(0, 0), (1, 0), (0, 1), (1, 1), (0, 2), (1, 2)]
        assert target == list(m.keys())

    def test_index_linear_to_tuple(self):
        m = Mesh(3, 4)
        for (i, (x, y)) in enumerate(m.keys()):
            assert m._index_linear_to_tuple(i) == (x, y)

    def test_index_tuple_to_linear(self):
        m = Mesh(3, 4)
        for (i, (x, y)) in enumerate(m.keys()):
            assert m._index_tuple_to_linear((x, y)) == i

    def test_getitem(self):
        m = Mesh(2, 2)
        m._data = [1, 2, 3, 4]
        assert m[0, 0] == 1
        assert m[1, 0] == 2
        assert m[0, 1] == 3
        assert m[1, 1] == 4
        with pytest.raises(KeyError):
            m.__getitem__((3, 0))
        with pytest.raises(KeyError):
            m.__getitem__((-1, 0))
        with pytest.raises(KeyError):
            m.__getitem__((0, 3))
        with pytest.raises(KeyError):
            m.__getitem__((0, -1))
        assert m.get((0, 0), 10) == 1
        assert m.get((1, 0), 10) == 2
        assert m.get((0, 1), 10) == 3
        assert m.get((1, 1), 10) == 4
        assert m.get((3, 0), 10) == 10
        assert m.get((-1, 0), 10) == 10
        assert m.get((0, 3), 10) == 10
        assert m.get((0, -1), 10) == 10

    def test_setitem(self):
        m = Mesh(2, 2)
        m[0, 0] = 1
        m[1, 0] = 2
        m[0, 1] = 3
        m[1, 1] = 4
        assert m._data == [1, 2, 3, 4]
        with pytest.raises(KeyError):
            m.__setitem__((3, 0), 1)
        with pytest.raises(KeyError):
            m.__setitem__((-1, 0), 1)
        with pytest.raises(KeyError):
            m.__setitem__((0, 3), 1)
        with pytest.raises(KeyError):
            m.__setitem__((0, -1), 1)

    def test_iter(self):
        m = Mesh(2, 3)
        assert [i for i in m] == [(0, 0), (1, 0), (0, 1), (1, 1), (0, 2), (1, 2)]

    def test_set_data(self):
        m = Mesh(2, 2)
        m._set_data([1, 2, 3, 4])
        assert list(m.values()) == [1, 2, 3, 4]
        with pytest.raises(TypeError):
            m._set_data('abcd')
        with pytest.raises(ValueError):
            m._set_data([1, 2, 3])

    def test_init_data(self):
        m = Mesh(2, 2, data=[1, 2, 3, 4])
        assert list(m.values()) == [1, 2, 3, 4]
        with pytest.raises(TypeError):
            Mesh(2, 2, data='abcd')
        with pytest.raises(ValueError):
            Mesh(2, 2, data=[1, 2, 3])

    def test_len(self):
        m = Mesh(2, 2)
        assert len(m) == 4

    def test_str(self):
        m = Mesh(2, 3, data=[1, 2, 3, 4, 5, 6])
        assert str(m) == '[1, 2]\n[3, 4]\n[5, 6]\n'

    def test_compact_str(self):
        m = Mesh(2, 3, data=[1, 2, 3, 4, 5, 6])
        assert m.compact_str == '12\n34\n56\n'
        m = Mesh(3, 2, data=[1, 2, 3, 4, 5, 6])
        assert m.compact_str == '123\n456\n'

    def test_equality(self):
        m1a = Mesh(2, 2, data=[1, 2, 3, 4])
        m1b = Mesh(2, 2, data=[1, 2, 3, 4])
        m2 = Mesh(2, 2, data=[1, 2, 3, 5])
        assert m1a == m1b
        assert m1a == m1a
        assert m1a != m2
        assert m2 != m1a
        assert m1a != None
        assert None != m1a

    def test_repr(self):
        m = Mesh(2, 2, data=[1, 2, 3, 4])
        m2 = eval(repr(m))
        assert m == m2

    def test_repr_2(self):
        # check that types work
        data=["1", 2.0, 3, 4]
        m = Mesh(2, 2, data=list(data))
        m2 = eval(repr(m))
        assert m == m2
        assert data == m2._data

    def test_copy(self):
        m = Mesh(2, 2)
        m2 = m
        m3 = m.copy()
        m[1, 1] = True
        assert m2[1, 1]
        assert not m3[1, 1]

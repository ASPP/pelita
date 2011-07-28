# -*- coding: utf-8 -*-

import unittest
import json

from pelita.messaging.json_convert import JsonConverter, json_id

@json_id("pelita.test.A")
class A(object):
    def __init__(self, a):
        self.a = a

    def _to_json_dict(self):
        return {"a": self.a}

    @classmethod
    def _from_json_dict(cls, item):
        return cls(**item)

    def __eq__(self, other):
        return self.a == other.a

@json_id("pelita.test.B")
class B(object):
    def __init__(self, b, *a_values):
        self.b = b
        self.a_values = a_values

    def _to_json_dict(self):
        return {"b": self.b,
                "a_values": self.a_values}

    @classmethod
    def _from_json_dict(cls, item):
        b = item["b"]
        a_values = item["a_values"]
        return cls(b, *a_values)

    def __eq__(self, other):
        return self.b == other.b and self.a_values == other.a_values


class TestJson(unittest.TestCase):
    def test_can_encode(self):
        converter = JsonConverter()
        converter.register(A)

        a = A(['1', '2', '3'])
        encoded = json.dumps(a, default=converter.encode)

        should_be = {"__id__": "pelita.test.A", "__value__": {"a": ["1", "2", "3"]}}
        decoded = json.loads(encoded)
        self.assertEqual(decoded, should_be)

    def test_can_decode(self):
        converter = JsonConverter()
        converter.register(A)

        json_code = """{"__id__": "pelita.test.A", "__value__": {"a": ["1", "2", "3"]}}"""

        decoded = json.loads(json_code, object_hook=converter.decode)

        a = A(['1', '2', '3'])
        self.assertEqual(decoded, a)

    def test_can_recode_nested(self):
        converter = JsonConverter()
        converter.register(A, encoder=A._to_json_dict, decoder=A._from_json_dict)
        converter.register(B)

        a1 = A(1)
        a2 = A("2")
        a3 = A(['1', '2', '3'])
        bb = B("B", a1, a2, a3)

        dumped = json.dumps(bb, default=converter.encode)
        loaded = json.loads(dumped, object_hook=converter.decode)

        self.assertEqual(bb, loaded)

    def test_encoding_methods(self):
        converter = JsonConverter()

        def encoder(obj):
            return {"a": [val * 2 for val in obj.a]}

        def decoder(obj):
            obj["a"] = [val // 2 for val in obj["a"]]
            return A(**obj)

        converter.register(A, encoder=encoder, decoder=decoder)
        a = A([1, 2, 3])
        res = json.dumps(a, default=converter.encode)
        res_dict = json.loads(res)

        self.assertEqual(res_dict, {"__id__": "pelita.test.A", "__value__": {"a": [2, 4, 6]}})

        reencoded = json.loads(res, object_hook=converter.decode)

        self.assertEqual(a, reencoded)

    def test_wrong_classes(self):
        converter = JsonConverter()

        class NoId(object):
            def _to_json_dict(self):
                return {}

            @classmethod
            def _from_json_dict(cls, item):
                return cls()

        self.assertRaises(ValueError, converter.register, NoId)

        @json_id("pelita.test.NoToDict")
        class NoToDict(object):
            @classmethod
            def _from_json_dict(cls, item):
                return cls()

        self.assertRaises(ValueError, converter.register, NoToDict)

        @json_id("pelita.test.NoFromDict")
        class NoFromDict(object):
            def _to_json_dict(self):
                return {}

        self.assertRaises(ValueError, converter.register, NoFromDict)

        @json_id("pelita.test.BadToDict")
        class BadToDict(object):
            @classmethod
            def _to_json_dict(cls, item):
                return {}

            @classmethod
            def _from_json_dict(cls, item):
                return cls()

        self.assertRaises(ValueError, converter.register, BadToDict)

        @json_id("pelita.test.BadFromDict")
        class BadFromDict(object):
            def _to_json_dict(self):
                return {}

            def _from_json_dict(item):
                return item

        self.assertRaises(ValueError, converter.register, BadFromDict)

    def test_double_identifier(self):
        class AA(A):
            pass
        converter = JsonConverter()
        converter.register(A)
        self.assertRaises(ValueError, converter.register, AA)

    def test_unknown(self):
        converter = JsonConverter()
        converter.register(A)

        unknown_json = """{"__id__": "unknown", "__value__": {"a": [2, 4, 6]}}"""
        res_with_converter = json.loads(unknown_json, object_hook=converter.decode)
        res_without_converter = json.loads(unknown_json, object_hook=converter.decode)

        self.assertEqual(res_with_converter, res_without_converter)

    def test_unregistered(self):
        converter = JsonConverter()
        a = A("value")

        self.assertRaises(TypeError, json.dumps, a, default=converter.encode)

    def test_autoregistration(self):
        json_converter = JsonConverter()

        @json_converter.serializable("pelita.test.Autoserialize")
        class Autoserialize(object):
            def __init__(self, value):
                self.value = value

            def _to_json_dict(self):
                return {"value": self.value}

            @classmethod
            def _from_json_dict(cls, item):
                return cls(**item)

            def __eq__(self, other):
                return self.value == other.value

        autoserialize = Autoserialize("a value")
        converted = json.dumps(autoserialize, default=json_converter.encode)
        reencoded = json.loads(converted, object_hook=json_converter.decode)

        self.assertEqual(autoserialize, reencoded)



# TODO: Think about rules for inheritance
#
#    def test_child(self):
#        converter = JsonConverter()
#        converter.register(A)
#
#        class AA(A):
#            def __init__(self, a):
#                self.a = a
#
#        aa = AA("q")
#
#        dumped = json.dumps(aa, default=converter.encode)
#        loaded = json.loads(dumped, object_hook=converter.decode)
#        print loaded

if __name__ == "__main__":
    unittest.main()

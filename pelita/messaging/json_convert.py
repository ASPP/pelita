# -*- coding: utf-8 -*-

""" Json conversion helpers. """

import inspect
import json

__docformat__ = "restructuredtext"


class JsonConverter(object):
    """ The `JsonConverter` registers all necessary methods to transform
    an object into a Json understandable format and back again.

    This format is a simple dict of the form::

        {"__id__": json_id,
         "__value__": unique serialisation}

    With the help of the json_id, it is possible to match the dict
    to a specific class and encoder. This id is essential to the whole
    process, so that a class attribute `_json_id` needs to be set in every
    class which wants to use serialisation.

    Either::

        class MyObject(object):
            _json_id = "module.MyObject"

    or::

        @json_id("module.MyObject")
        class MyObject(object):
            pass
    """
    def __init__(self):
        self.reg = {}

    def _guess_encoder(self, class_):
        """ Guesses the standard encoder as `class_._to_json_dict` and
        checks that this method is available.
        """
        try:
            encoder = getattr(class_, "_to_json_dict")

            # trick to find out, if "from_dict" is an instancemethod
            # may also raise AttributeError
            if inspect.isclass(encoder.__self__):
                raise ValueError("Class '%s' has no instancemethod '_to_json_dict'." % class_.__name__)
        except AttributeError:
            raise ValueError("Class '%s' has no instancemethod '_to_json_dict'." % class_.__name__)
        return encoder

    def _guess_decoder(self, class_):
        """ Guesses the standard decoder as `class_._from_json_dict` and
        checks that this method is available and is a classmethod.
        """
        try:
            decoder = getattr(class_, "_from_json_dict")

            # trick to find out, if "from_dict" is a classmethod
            # may also raise AttributeError
            if not inspect.isclass(decoder.__self__):
                raise ValueError("Class '%s' has no classmethod '_from_json_dict'." % class_.__name__)
        except AttributeError:
            raise ValueError("Class '%s' has no classmethod '_from_json_dict'." % class_.__name__)
        return decoder


    def register(self, class_, encoder=None, decoder=None):
        """ Registers `class_` in the conversion registry with
        respective `encoder` and `decoder` methods.

        `class_` must have a class attribute "_json_id" which holds
         a unique identifier.

        Parameters
        ----------
        class_ : dict
            The class whose serialisation methods need to be registered.

        encoder : function
            function which transforms an object of class_ to a dict
            (defaults to "_to_json_dict" instance method)

        decoder : function
            function which transforms a dict to an instance of class_
            (defaults to "_from_json_dict" class method)
        """
        try:
            identifier = class_._json_id
        except AttributeError:
            raise ValueError("Class '%s' has no attribute '_json_id'.")

        if identifier in self.reg:
            raise ValueError("%r is already a registered identifier." % identifier)

        if not encoder:
            encoder = self._guess_encoder(class_)

        if not decoder:
            decoder = self._guess_decoder(class_)

        self.reg[identifier] = {"class": class_,
                                "encoder": encoder,
                                "decoder": decoder}

    def encode(self, item):
        """ Calls the necessary functions to turn `item` into
        a plain dictionary which can be serialised.

        Parameters
        ----------
        item : obj
            An object which needs to be serialised

        Returns
        -------
        dict : dict containing the keys "__id__" and "__value__"
            returns serialised object as "__value__"
        """
        try:
            json_id = item._json_id
        except AttributeError:
            # json.dump wants a TypeError, if we cannot match it
            raise TypeError('%r is not JSON serializable. (No "_json_id" attribute.)' % item)

        try:
            converter = self.reg[json_id]
        except KeyError:
            # json.dump wants a TypeError, if we cannot match it
            raise TypeError('%r is not JSON serializable.' % item)

        res = dict()
        res["__id__"] = json_id
        res["__value__"] = converter["encoder"](item)
        return res

    def decode(self, json_dict):
        """ Receives a dictionary `json` and tries to match it
        on a registered class.

        Parameters
        ----------
        json_dict : dict
            A dict which shall be decoded to an object.

        Returns
        -------
        obj : dict or more specific object instance
            returns the matched and restored object instance or
            the original dict in case of failure
        """
        try:
            json_id = json_dict["__id__"]
            value = json_dict["__value__"]
            converter = self.reg[json_id]
        except KeyError:
            # we don’t know any better, let’s hope the best
            return json_dict

        obj = converter["decoder"](value)
        return obj


    def serializable(self, cls_or_id):
        if isinstance(cls_or_id, basestring):
            id = cls_or_id
        elif inspect.isclass(cls_or_id):
            id = "%s.%s" % (cls_or_id.__module__, cls_or_id.__name__)
        else:
            raise TypeError("Argument for decorator must be string or class.")

        def wrapper(class_):
            class_._json_id = id
            self.register(class_)
            return class_

        if inspect.isclass(cls_or_id):
            return wrapper(cls_or_id)

        return wrapper

    def dumps(self, obj):
        return json.dumps(obj, default=self.encode)

    def loads(self, json_dict):
        return json.loads(json_dict, object_hook=self.decode)

def json_id(id):
    def wrapper(cls):
        cls._json_id = id
        return cls
    return wrapper

# default serialization helpers
json_converter = JsonConverter()
serializable = json_converter.serializable

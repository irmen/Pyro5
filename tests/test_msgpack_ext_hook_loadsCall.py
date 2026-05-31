"""
Regression test: MsgpackSerializer.loadsCall must honor ext_hook so that
ExtType-encoded call arguments round-trip when a subclass overrides
ext_hook to handle custom codes. The sibling loads() has always passed
both hooks; loadsCall used to pass only object_hook.
"""
import unittest

import msgpack

import Pyro5.serializers as serializers


CUSTOM_EXT_CODE = 0x40


class Thing:
    def __init__(self, value):
        self.value = value


class CustomMsgpackSerializer(serializers.MsgpackSerializer):
    def default(self, obj):
        if isinstance(obj, Thing):
            return msgpack.ExtType(CUSTOM_EXT_CODE, str(obj.value).encode("ascii"))
        return super().default(obj)

    def ext_hook(self, code, data):
        if code == CUSTOM_EXT_CODE:
            return Thing(int(data))
        return super().ext_hook(code, data)


class TestMsgpackExtHookLoadsCall(unittest.TestCase):
    def test_loadsCall_honors_ext_hook(self):
        """
        Pack a call message whose first vararg is a custom-ExtType-encoded
        object and verify loadsCall reconstructs it via the subclass's
        ext_hook. Before the fix this returned msgpack.ExtType, not Thing.
        """
        ser = CustomMsgpackSerializer()
        data = ser.dumpsCall("obj-id", "method-name", (Thing(42),), {})
        obj, method, vargs, kwargs = ser.loadsCall(data)
        self.assertEqual(obj, "obj-id")
        self.assertEqual(method, "method-name")
        self.assertIsInstance(vargs[0], Thing)
        self.assertEqual(vargs[0].value, 42)
        self.assertEqual(kwargs, {})

    def test_loads_already_honors_ext_hook(self):
        """
        Symmetric sanity check on the working sibling path. Would have
        passed before the fix too; included so future regressions on
        either method surface symmetrically.
        """
        ser = CustomMsgpackSerializer()
        data = ser.dumps(Thing(7))
        back = ser.loads(data)
        self.assertIsInstance(back, Thing)
        self.assertEqual(back.value, 7)


if __name__ == "__main__":
    unittest.main()

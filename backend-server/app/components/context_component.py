# backend/components/context_component.py
import time

class ContextComponent:
    """
    Very lightweight context-aware engine.
    You can expand rules to include time windows, geo-IP, device fingerprint, etc.
    """
    def __init__(self):
        # sample context policies store (in real system use policy language)
        self.policies = {}

    def add_policy(self, file_id, policy):
        # policy: dict with possible keys like allowed_locations, allowed_times, allowed_devices
        self.policies[file_id] = policy

    def check_access(self, file_id, context):
        """
        context: {time: epoch, location: 'india', device_id: 'dev1', department: 'cs'}
        Returns True if passes, False if violates.
        Simple rules:
        - if allowed_locations present -> check membership
        - if time_range -> check
        """
        pol = self.policies.get(file_id)
        if not pol:
            return True

        # location
        if "allowed_locations" in pol:
            if context.get("location") not in pol["allowed_locations"]:
                return False

        # time restrict (start, end) epoch
        if "time_window" in pol and isinstance(pol["time_window"], (list, tuple)) and len(pol["time_window"]) == 2:
            start, end = pol["time_window"]
            t = context.get("time", time.time())
            if not (start <= t <= end):
                return False

        # device whitelist
        if "allowed_devices" in pol:
            if context.get("device_id") not in pol["allowed_devices"]:
                return False

        return True

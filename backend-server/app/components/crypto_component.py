import os
import base64
from typing import Any, Dict
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import json

try:
    from charm.toolbox.pairinggroup import PairingGroup, GT
    from charm.schemes.abenc.waters11 import Waters11
    from charm.core.engine.util import objectToBytes, bytesToObject
except Exception as e:
    PairingGroup = None
    Waters11 = None

# -------------------- Helpers --------------------
def _aes_encrypt_file(input_path: str, output_path: str, key: bytes):
    """Encrypt a file using AES-GCM."""
    cipher = AES.new(key, AES.MODE_GCM)
    with open(input_path, "rb") as f:
        plaintext = f.read()
    ciphertext, tag = cipher.encrypt_and_digest(plaintext)
    with open(output_path, "wb") as f:
        f.write(cipher.nonce + tag + ciphertext)

def _aes_decrypt_file(input_path: str, output_path: str, key: bytes):
    """Decrypt a file encrypted with AES-GCM."""
    with open(input_path, "rb") as f:
        nonce = f.read(16)
        tag = f.read(16)
        ciphertext = f.read()
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    plaintext = cipher.decrypt_and_verify(ciphertext, tag)
    with open(output_path, "wb") as f:
        f.write(plaintext)

# -------------------- Crypto Component --------------------
class CryptoComponent:
    """Wrapper for Charm CP-ABE (Waters11) with hybrid AES file encryption."""

    def __init__(self, curve: str = "SS512", uni_size: int = 100):
        if PairingGroup is None or Waters11 is None:
            raise RuntimeError(
                "Charm-Crypto CP-ABE classes not available. "
                "Install charm-crypto in your environment (pip install charm-crypto)"
            )

        self.group = PairingGroup(curve)
        self.cpabe = Waters11(self.group, uni_size, verbose=False)

        self._pk_b64: str | None = None
        self._msk_b64: str | None = None

        self.keys_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "keys"))
        os.makedirs(self.keys_folder, exist_ok=True)

    # ---------- Serialization helpers ----------
    def _b64_obj(self, obj: Any) -> str:
        if obj is None:
            raise ValueError("Cannot serialize None object - CP-ABE operation likely failed")
        try:
            return base64.b64encode(objectToBytes(obj, self.group)).decode("utf-8")
        except Exception as e:
            raise ValueError(f"Failed to serialize CP-ABE object: {e}")

    def _obj_from_b64(self, s: str):
        try:
            return bytesToObject(base64.b64decode(s.encode("utf-8")), self.group)
        except Exception as e:
            raise ValueError(f"Failed to deserialize CP-ABE object: {e}")

    # ---------- WATERS11-COMPATIBLE NORMALIZATION ----------
    def _normalize_attributes(self, attributes: list[str]) -> list[str]:
        """Normalize attributes to numeric format for Waters11."""
        attr_map = {
            'role:prof': '1', 'role:student': '2', 'role:admin': '3',
            'dept:cs': '10', 'dept:math': '11', 'dept:eng': '12'
        }
        
        normalized = []
        for attr in attributes:
            if attr in attr_map:
                normalized.append(attr_map[attr])
            else:
                # Hash unknown attributes to numbers
                normalized.append(str(abs(hash(attr)) % 50 + 1))
        
        print(f"Normalized attributes: {normalized}")
        return normalized

    def _normalize_policy(self, policy: str) -> str:
        """Convert policy to Waters11-compatible format."""
        if not policy or not policy.strip():
            raise ValueError("Policy cannot be empty")
        
        # Map policy terms to numeric format
        attr_map = {
            'role:prof': '1', 'ROLE_PROF': '1', 'prof': '1',
            'role:student': '2', 'ROLE_STUDENT': '2', 'student': '2', 
            'role:admin': '3', 'ROLE_ADMIN': '3', 'admin': '3',
            'dept:cs': '10', 'DEPT_CS': '10', 'cs': '10',
            'dept:math': '11', 'DEPT_MATH': '11', 'math': '11',
            'dept:eng': '12', 'DEPT_ENG': '12', 'eng': '12'
        }
        
        normalized = policy.strip()
        for key, value in attr_map.items():
            normalized = normalized.replace(key, value)
        
        print(f"Normalized policy: {normalized}")
        return normalized

    # ---------------- Setup / Keys ----------------
    def setup(self, force: bool = False):
        if self._pk_b64 and self._msk_b64 and not force:
            return
        print("Setting up Waters11 CP-ABE master keys...")
        try:
            pk, msk = self.cpabe.setup()
            print(f"Generated PK type: {type(pk)}, MSK type: {type(msk)}")
            self._pk_b64 = self._b64_obj(pk)
            self._msk_b64 = self._b64_obj(msk)
            print("Waters11 master keys setup complete")
        except Exception as e:
            print(f"Waters11 setup failed: {e}")
            raise

    def save_master_keys(self, name: str = "master"):
        if not self._pk_b64 or not self._msk_b64:
            raise RuntimeError("Keys not initialized. Call setup() first.")
        with open(os.path.join(self.keys_folder, f"{name}_pk.b64"), "w") as f:
            f.write(self._pk_b64)
        with open(os.path.join(self.keys_folder, f"{name}_msk.b64"), "w") as f:
            f.write(self._msk_b64)

    def load_master_keys(self, name: str = "master"):
        pk_path = os.path.join(self.keys_folder, f"{name}_pk.b64")
        msk_path = os.path.join(self.keys_folder, f"{name}_msk.b64")
        if not os.path.exists(pk_path) or not os.path.exists(msk_path):
            raise FileNotFoundError("Master keys not found. Run setup() first.")
        with open(pk_path, "r") as f:
            self._pk_b64 = f.read().strip()
        with open(msk_path, "r") as f:
            self._msk_b64 = f.read().strip()

    def _get_pk_msk(self):
        if not self._pk_b64 or not self._msk_b64:
            raise RuntimeError("Keys not loaded.")
        return self._obj_from_b64(self._pk_b64), self._obj_from_b64(self._msk_b64)

    def generate_user_secret(self, attributes: list[str]) -> str:
        pk, msk = self._get_pk_msk()
        norm_attrs = self._normalize_attributes(attributes)
        print(f"Generating Waters11 user secret for attributes: {norm_attrs}")
        try:
            sk = self.cpabe.keygen(pk, msk, norm_attrs)
            if sk is None:
                raise ValueError("Failed to generate user secret key")
            print(f"Generated Waters11 SK type: {type(sk)}")
            return self._b64_obj(sk)
        except Exception as e:
            print(f"Waters11 key generation failed: {e}")
            raise

    # ✅ FIXED: Serialize only group elements, handle policy separately
    def _serialize_ciphertext(self, ct: dict) -> dict:
        """Serialize each GROUP ELEMENT in the ciphertext dict to base64 string."""
        ser_ct = {}
        
        # Skip 'policy' since it's not a group element
        group_element_keys = ['c0', 'C', 'D', 'c_m']
        
        for key in group_element_keys:
            if key in ct:
                if key in ['C', 'D']:
                    # C and D are dictionaries of group elements
                    ser_ct[key] = {}
                    for attr, elem in ct[key].items():
                        ser_ct[key][attr] = base64.b64encode(objectToBytes(elem, self.group)).decode("utf-8")
                else:
                    # c0 and c_m are single group elements
                    ser_ct[key] = base64.b64encode(objectToBytes(ct[key], self.group)).decode("utf-8")
        
        return ser_ct

    def _deserialize_ciphertext(self, ser_ct: dict) -> dict:
        """Deserialize each element in ciphertext dict from base64 string."""
        ct = {}
        
        for key, value in ser_ct.items():
            if key in ['C', 'D']:
                # C and D are dictionaries of group elements
                ct[key] = {}
                for attr, elem_b64 in value.items():
                    ct[key][attr] = bytesToObject(base64.b64decode(elem_b64.encode("utf-8")), self.group)
            else:
                # c0 and c_m are single group elements
                ct[key] = bytesToObject(base64.b64decode(value.encode("utf-8")), self.group)
        
        return ct

    # ---------------- String Encryption ----------------
    def abe_encrypt_str(self, policy: str, plaintext: str) -> str:
        pk, _ = self._get_pk_msk()
        
        normalized_policy = self._normalize_policy(policy)
        
        print(f"Encrypting with Waters11 policy: '{normalized_policy}', plaintext length: {len(plaintext)}")
        
        try:
            # Generate random GT element and encrypt that
            random_msg = self.group.random(GT)
            ct = self.cpabe.encrypt(pk, random_msg, normalized_policy)
            if ct is None:
                raise ValueError("Waters11 encryption returned None")
            print(f"Waters11 encryption successful, ciphertext type: {type(ct)}")
            
            # ✅ FIXED: Serialize only group elements, store policy separately
            ser_ct = self._serialize_ciphertext(ct)
            
            result = {
                'ct': ser_ct,
                'random_msg_b64': self._b64_obj(random_msg),
                'plaintext': plaintext,
                'policy_str': normalized_policy  # Store policy string separately
            }
            
            return json.dumps(result)
            
        except Exception as e:
            print(f"Waters11 encryption failed: {e}")
            raise ValueError(f"Waters11 encryption failed: {e}")

    def abe_decrypt_str(self, ct_json: str, user_sk_b64: str) -> str:
        pk, _ = self._get_pk_msk()
        sk = self._obj_from_b64(user_sk_b64)
        
        try:
            # Parse JSON and deserialize components separately
            result = json.loads(ct_json)
            ct_group_elements = self._deserialize_ciphertext(result['ct'])
            random_msg = self._obj_from_b64(result['random_msg_b64'])
            
            # ✅ FIXED: Reconstruct the policy object for decryption
            policy_str = result['policy_str']
            policy_obj = self.cpabe.util.createPolicy(policy_str)
            ct_group_elements['policy'] = policy_obj
            
            # Decrypt the random message
            decrypted_msg = self.cpabe.decrypt(pk, ct_group_elements, sk)
            if decrypted_msg is None:
                raise ValueError("Waters11 decryption failed - policy not satisfied")
            
            # Verify the decrypted message matches what we encrypted
            if decrypted_msg == random_msg:
                return result['plaintext']
            else:
                raise ValueError("Waters11 decryption verification failed")
        except Exception as e:
            raise ValueError(f"Waters11 decryption failed: {e}")

    # ---------------- Hybrid File Encryption ----------------
    def encrypt_file_hybrid(self, file_path: str, policy: str) -> Dict[str, Any]:
        """Encrypt file using AES + encrypt AES key with Waters11 CP-ABE."""
        aes_key = get_random_bytes(32)
        enc_file_path = file_path + ".enc"
        _aes_encrypt_file(file_path, enc_file_path, aes_key)

        aes_key_hex = aes_key.hex()
        print(f"Encrypting AES key with Waters11 policy: {policy}")
        abe_ct_json = self.abe_encrypt_str(policy, aes_key_hex)

        return {
            "orig_filename": os.path.basename(file_path),
            "enc_file_path": enc_file_path,
            "abe_ct": abe_ct_json,
            "policy": policy,
        }

    def decrypt_file_hybrid(self, meta: Dict[str, Any], user_sk_b64: str, out_plain_path: str = None) -> str:
        """Decrypt file using Waters11 ABE SK to recover AES key, then AES-decrypt file."""
        aes_key_hex = self.abe_decrypt_str(meta["abe_ct"], user_sk_b64)
        aes_key = bytes.fromhex(aes_key_hex)

        if not out_plain_path:
            out_plain_path = os.path.join(
                self.keys_folder, f"dec_{os.path.basename(meta['orig_filename'])}"
            )

        _aes_decrypt_file(meta["enc_file_path"], out_plain_path, aes_key)
        return out_plain_path

if __name__ == "__main__":
    cc = CryptoComponent()
    cc.setup(force=True)
    cc.save_master_keys()
    # test user + file  
    user_sk = cc.generate_user_secret(["role:admin"])
    meta = cc.encrypt_file_hybrid("test.txt", "role:admin")
    dec_path = cc.decrypt_file_hybrid(meta, user_sk)
    print("Decrypted file saved to:", dec_path)

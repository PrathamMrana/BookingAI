import unittest
from werkzeug.security import generate_password_hash, check_password_hash

class TestUserAuth(unittest.TestCase):

    def test_generate_password_hash(self):
        """
        Test that generate_password_hash produces a non-empty string
        and that the hash is different from the original password.
        """
        password = "plain_password123"
        hashed_password = generate_password_hash(password)

        self.assertIsNotNone(hashed_password, "Hashed password should not be None.")
        self.assertIsInstance(hashed_password, str, "Hashed password should be a string.")
        self.assertNotEqual(password, hashed_password, "Hashed password should not be the same as the plain password.")
        self.assertTrue(len(hashed_password) > 0, "Hashed password should not be an empty string.")

    def test_check_password_hash_correct_password(self):
        """
        Test that check_password_hash returns True for the correct password.
        """
        password = "correct_password@Secure"
        hashed_password = generate_password_hash(password)
        
        self.assertTrue(check_password_hash(hashed_password, password),
                        "check_password_hash should return True for the correct password.")

    def test_check_password_hash_incorrect_password(self):
        """
        Test that check_password_hash returns False for an incorrect password.
        """
        correct_password = "correct_password@Secure"
        incorrect_password = "incorrect_password@Oops"
        hashed_password = generate_password_hash(correct_password)
        
        self.assertFalse(check_password_hash(hashed_password, incorrect_password),
                         "check_password_hash should return False for an incorrect password.")

    def test_check_password_hash_empty_password(self):
        """
        Test that check_password_hash handles empty passwords correctly.
        (Assuming empty passwords are not allowed or will result in a specific hash)
        """
        password = ""
        hashed_password = generate_password_hash(password) # Werkzeug handles empty strings
        
        self.assertTrue(check_password_hash(hashed_password, password),
                        "check_password_hash should correctly validate an empty password if it was hashed.")
        self.assertFalse(check_password_hash(hashed_password, "non_empty_password"),
                         "check_password_hash should return False for non-empty password against empty password's hash.")

    def test_check_password_hash_different_hashes_for_same_password(self):
        """
        Test that generate_password_hash produces different hashes for the same password
        due to salting, but check_password_hash still works.
        """
        password = "same_password_for_hashing"
        hash1 = generate_password_hash(password)
        hash2 = generate_password_hash(password)

        self.assertNotEqual(hash1, hash2, "Two hashes for the same password should be different due to salting.")
        self.assertTrue(check_password_hash(hash1, password), "check_password_hash should validate hash1.")
        self.assertTrue(check_password_hash(hash2, password), "check_password_hash should validate hash2.")

if __name__ == '__main__':
    unittest.main()

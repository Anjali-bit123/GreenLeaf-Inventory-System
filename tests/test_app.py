import os, tempfile, unittest
from app import app
from database import init_db

class GreenLeafTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False)
        self.tmp.close()
        app.config.update(TESTING=True, DATABASE=self.tmp.name, SECRET_KEY="test-secret")
        with app.app_context():
            init_db()
        self.client = app.test_client()
        self.client.get("/seed-demo")

    def tearDown(self):
        os.unlink(self.tmp.name)

    def login(self, username="admin", password="Admin@123"):
        return self.client.post("/login", data={"username": username, "password": password})

    def test_login_success(self):
        response = self.login()
        self.assertEqual(response.status_code, 302)

    def test_login_invalid_password(self):
        response = self.client.post("/login", data={"username":"admin","password":"wrong"})
        self.assertIn(b"Invalid username", response.data)

    def test_dashboard_requires_login(self):
        self.assertEqual(self.client.get("/dashboard").status_code, 302)

    def test_dashboard_after_login(self):
        self.login()
        self.assertEqual(self.client.get("/dashboard").status_code, 200)

    def test_products_page(self):
        self.login()
        self.assertEqual(self.client.get("/products").status_code, 200)

    def test_product_search(self):
        self.login()
        self.assertEqual(self.client.get("/products?q=Rice").status_code, 200)

    def test_billing_page(self):
        self.login()
        self.assertEqual(self.client.get("/billing").status_code, 200)

    def test_reports_page(self):
        self.login()
        self.assertEqual(self.client.get("/reports").status_code, 200)

    def test_staff_cannot_update_product(self):
        self.login("staff", "Staff@123")
        response = self.client.post("/products/1/update", data={"price":"1","stock":"2","reorder_level":"1"})
        self.assertEqual(response.status_code, 302)

    def test_negative_product_rejected(self):
        self.login()
        self.client.post("/products", data={"name":"Bad","category":"Test","price":"-1","stock":"1","reorder_level":"1"})
        with app.app_context():
            from database import get_db
            count = get_db().execute("SELECT COUNT(*) FROM products WHERE name='Bad'").fetchone()[0]
            self.assertEqual(count, 0)

if __name__ == "__main__":
    unittest.main()

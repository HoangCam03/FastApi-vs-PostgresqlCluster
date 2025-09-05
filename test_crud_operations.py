#!/usr/bin/env python3
"""
Test CRUD Operations for PostgreSQL Cluster
Script để test các thao tác Create, Read, Update, Delete trên PostgreSQL cluster
"""

###Test CRUD qua HTTP API (FastAPI), có login, tạo/sửa/xem/xóa User và Post, bulk.
##Mục tiêu: Chứng minh ở tầng ứng dụng: endpoint ghi dùng session Primary, endpoint đọc dùng Replica (nơi đã cấu hình), hành vi phù hợp kiến trúc.

import requests
import json
import time
import sys
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

# Configuration
BASE_URL = "https://localhost:8443"
API_BASE = f"{BASE_URL}/api"
LOGIN_URL = f"{API_BASE}/auth/login"

# Test data
TEST_USER = {
    "username": "test_user",
    "email": "test@example.com",
    "password": "test123456"
}

TEST_POST = {
    "title": "Test Post for Cluster",
    "content": "This is a test post to verify cluster replication",
    "excerpt": "Test excerpt",
    "kol_id": 1,
    "category_id": 1
}

class ClusterTester:
    def __init__(self):
        self.access_token = None
        self.session = requests.Session()
        self.session.verify = False  # Disable SSL verification for testing
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
        
    def login(self):
        """Login để lấy access token"""
        try:
            response = self.session.post(LOGIN_URL, json={
                "username": "admin",
                "password": "admin123"
            })
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token")
                self.session.headers.update({
                    "Authorization": f"Bearer {self.access_token}"
                })
                self.log("✅ Login successful", "SUCCESS")
                return True
            else:
                self.log(f"❌ Login failed: {response.text}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Login error: {str(e)}", "ERROR")
            return False
    
    def test_user_crud(self):
        """Test CRUD operations cho User"""
        self.log("=== TESTING USER CRUD OPERATIONS ===", "INFO")
        
        # CREATE
        self.log("Creating test user...", "INFO")
        create_response = self.session.post(f"{API_BASE}/users/create", json=TEST_USER)
        if create_response.status_code == 200:
            user_data = create_response.json()
            user_id = user_data["user"]["id"]
            self.log(f"✅ User created with ID: {user_id}", "SUCCESS")
        else:
            self.log(f"❌ Failed to create user: {create_response.text}", "ERROR")
            return False
        
        # READ
        self.log("Reading user...", "INFO")
        read_response = self.session.get(f"{API_BASE}/users/{user_id}")
        if read_response.status_code == 200:
            self.log("✅ User read successful", "SUCCESS")
        else:
            self.log(f"❌ Failed to read user: {read_response.text}", "ERROR")
        
        # UPDATE
        self.log("Updating user...", "INFO")
        update_data = {"email": "updated@example.com"}
        update_response = self.session.put(f"{API_BASE}/users/{user_id}", json=update_data)
        if update_response.status_code == 200:
            self.log("✅ User updated successful", "SUCCESS")
        else:
            self.log(f"❌ Failed to update user: {update_response.text}", "ERROR")
        
        # DELETE
        self.log("Deleting user...", "INFO")
        delete_response = self.session.delete(f"{API_BASE}/users/{user_id}")
        if delete_response.status_code == 200:
            self.log("✅ User deleted successful", "SUCCESS")
        else:
            self.log(f"❌ Failed to delete user: {delete_response.text}", "ERROR")
        
        return True
    
    def test_post_crud(self):
        """Test CRUD operations cho Post"""
        self.log("=== TESTING POST CRUD OPERATIONS ===", "INFO")
        
        # CREATE
        self.log("Creating test post...", "INFO")
        create_response = self.session.post(f"{API_BASE}/posts/", json=TEST_POST)
        if create_response.status_code == 200:
            post_data = create_response.json()
            post_id = post_data["post"]["id"]
            self.log(f"✅ Post created with ID: {post_id}", "SUCCESS")
        else:
            self.log(f"❌ Failed to create post: {create_response.text}", "ERROR")
            return False
        
        # READ
        self.log("Reading post...", "INFO")
        read_response = self.session.get(f"{API_BASE}/posts/{post_id}")
        if read_response.status_code == 200:
            self.log("✅ Post read successful", "SUCCESS")
        else:
            self.log(f"❌ Failed to read post: {read_response.text}", "ERROR")
        
        # UPDATE
        self.log("Updating post...", "INFO")
        update_data = {"title": "Updated Test Post"}
        update_response = self.session.put(f"{API_BASE}/posts/{post_id}", json=update_data)
        if update_response.status_code == 200:
            self.log("✅ Post updated successful", "SUCCESS")
        else:
            self.log(f"❌ Failed to update post: {update_response.text}", "ERROR")
        
        # DELETE
        self.log("Deleting post...", "INFO")
        delete_response = self.session.delete(f"{API_BASE}/posts/{post_id}")
        if delete_response.status_code == 200:
            self.log("✅ Post deleted successful", "SUCCESS")
        else:
            self.log(f"❌ Failed to delete post: {delete_response.text}", "ERROR")
        
        return True
    
    def test_bulk_operations(self):
        """Test bulk operations để tạo nhiều dữ liệu"""
        self.log("=== TESTING BULK OPERATIONS ===", "INFO")
        
        # Tạo nhiều users
        for i in range(5):
            user_data = {
                "username": f"bulk_user_{i}",
                "email": f"bulk{i}@example.com",
                "password": "test123456"
            }
            response = self.session.post(f"{API_BASE}/users/create", json=user_data)
            if response.status_code == 200:
                self.log(f"✅ Created bulk user {i+1}/5", "SUCCESS")
            else:
                self.log(f"❌ Failed to create bulk user {i+1}: {response.text}", "ERROR")
        
        # Tạo nhiều posts
        for i in range(10):
            post_data = {
                "title": f"Bulk Post {i+1}",
                "content": f"This is bulk post number {i+1} for cluster testing",
                "excerpt": f"Bulk excerpt {i+1}",
                "kol_id": 1,
                "category_id": 1
            }
            response = self.session.post(f"{API_BASE}/posts/", json=post_data)
            if response.status_code == 200:
                self.log(f"✅ Created bulk post {i+1}/10", "SUCCESS")
            else:
                self.log(f"❌ Failed to create bulk post {i+1}: {response.text}", "ERROR")
        
        return True
    
    def run_all_tests(self):
        """Chạy tất cả tests"""
        self.log("🚀 Starting PostgreSQL Cluster CRUD Tests", "INFO")
        
        if not self.login():
            return False
        
        tests = [
            self.test_user_crud,
            self.test_post_crud,
            self.test_bulk_operations
        ]
        
        for test in tests:
            try:
                test()
                time.sleep(1)  # Pause between tests
            except Exception as e:
                self.log(f"❌ Test failed: {str(e)}", "ERROR")
        
        self.log("🏁 All tests completed!", "INFO")
        return True

if __name__ == "__main__":
    tester = ClusterTester()
    tester.run_all_tests()

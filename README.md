# **Dining Hall Management System**

A web application for managing dining hall menus, food records, user requests, and administrative approvals. Designed to streamline the process of exploring food options, managing user feedback, and efficiently handling food requests.

---

## **Features**

### User Features:
- **View Dining Hall Menus**: Explore the food items offered in specific dining halls.
- **All Foods Page**: Browse and search through all available foods across dining halls.
- **Search Functionality**: Search for food items by name, category, or dining hall.
- **Pagination**: View large datasets in manageable chunks.
- **User Dashboard**: 
  - View personal information.
  - Access and manage personal records.
  - Check the status of submitted food requests.
- **Submit Food Requests**: Request new food items for dining halls.

### Admin Features:
- **Admin Dashboard**: 
  - View admin-specific information.
  - Access pending food requests for approval or denial.
  - Manage and view records created by the admin.
- **Request Approval/Denial Workflow**: Approve or reject user-submitted food requests.
- **Enhanced Sorting and Filtering**: Sort and filter food items dynamically.

---

## **Technologies Used**

- **Backend**:
  - Flask (Python)
  - SQLAlchemy (Database ORM)
  - PostgreSQL (Database)
- **Frontend**:
  - Jinja2 (Templating Engine)
  - HTML, CSS (Responsive Design)
  - JavaScript (Sorting and Filtering)

---

## **Installation**

### Prerequisites
1. **Python 3.10+**
2. **PostgreSQL**
3. **Virtual Environment (optional)**


## Usage

### **User Registration**:
Register as a user or log in with existing credentials.
Admin accounts need to be set up manually in the database.

### **Viewing Food and Dining Halls**:
Navigate through the All Foods or specific dining halls to explore food options.
Use search and sort functionality to narrow down results.

### **Managing Requests**:
Users can submit food requests via their dashboards.
Admins can approve or deny requests in the admin dashboard.

### **Adding Records**:
Users can add records for specific foods.
Admins have additional controls for managing records.

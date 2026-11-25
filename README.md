# Design and Development of a Web-Based Examination Process Management and Resource Optimization System

## Included modules
- Administrator login and password change
- Dashboard
- Theory and practical examination scheduling
- Student registration by branch-wise USN ranges (no individual student names)
- Room management and capacity records
- Automatic room allocation based on capacity and time availability
- General examination allotment
- Staff management
- Staff duty allocation with overlapping-time prevention
- Reports downloadable as CSV (opens in Excel)
- View / Edit / Delete through the vertical three-dot (⋮) Actions menu
- Indian Standard Time (IST) labels for all exam and duty times

## Requirements
- Python 3.10 or later
- Windows, macOS or Linux

## Run on Windows
1. Extract the ZIP.
2. Open the extracted folder in VS Code.
3. Open Terminal and run:

```powershell
py -m venv venv
venv\Scripts\activate
py -m pip install -r requirements.txt
py app.py
```

4. Open `http://127.0.0.1:5000` in your browser.

## Initial login
- Username: `admin`
- Password: `Admin@123`

Change the password from Settings after first login. For deployment beyond a local academic demonstration, set a unique `EMS_SECRET_KEY`, use HTTPS, turn off Flask debug mode, and use a production WSGI server.

## Recommended data-entry order
1. Add examination schedules (Theory or Practical).
2. Add branch-wise student USN ranges for each examination.
3. Add rooms with their actual seating capacities.
4. Open Resource Optimization and allocate rooms for an examination.
5. Add staff members.
6. Assign staff duties. A staff member cannot be assigned to two examinations whose date/time intervals overlap.
7. Review the Examination Allotment and Reports pages.

## USN range example
For Branch `ISE`, From USN `1`, To USN `15` means 15 students and displays as `001–015`. Add separate rows for ISE, ECE, CSE or other branches under the relevant examination.

## Resource allocation logic
The system assigns the registered USN ranges sequentially into available rooms, never exceeding each room's capacity. A room already assigned to an examination with an overlapping date/time is excluded. If total free capacity is insufficient, the transaction is rolled back and an error is displayed. This is a capacity-based heuristic; it does not calculate utilization percentages or recommend rooms.

## Important notes
- The system stores local examination dates and times as entered and labels them IST. Enter the correct Indian local time.
- Room allotment uses one exam schedule per selected examination record. If the same exam needs multiple independent sessions, create separate exam records.
- Deleting an examination also deletes its associated USN ranges, allotments and staff duties due to database relationships.
- Rooms and staff with existing history are deactivated rather than physically deleted, preserving records.
- Reports are CSV files, not PDFs.
- Back up `exam_management.db` regularly.

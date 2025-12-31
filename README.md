# Expense Management

A comprehensive expense management system for Frappe ERPNext that handles proper General Ledger entries following accounting standards.

## Features

### 1. Expense Types Management
- Create and manage different categories of expenses
- Set default expense accounts for each type
- Active/inactive status management

### 2. Expense Entry
- **Submittable Document**: Full workflow with draft, submit, and cancel states
- **Expense Details**: Date, type, description, and amount
- **Account Selection**: Choose from expense accounts and payment accounts
- **Payment Modes**: Cash, Bank, Credit Card, Debit Card, Cheque
- **Company-wise**: Multi-company support

### 3. Accounting Integration
- **Proper GL Entries**: Follows double-entry bookkeeping principles
- **Automatic GL Creation**: Creates debit/credit entries on submission
- **Preview Functionality**: Preview GL entries before submission
- **Account Validation**: Ensures proper account types are used

### 4. User Interface
- **Smart Forms**: Auto-populate expense accounts from expense types
- **Account Filtering**: Company-wise account filtering
- **Validation**: Client and server-side validations
- **Preview Button**: View GL entries before submission

### 5. Reporting
- **Expense Summary Report**: Comprehensive expense analysis
- **Filtering Options**: By date range, expense type, accounts, status
- **Export Capabilities**: Excel and PDF exports

## Installation

1. Install the app in your Frappe bench:
```bash
bench get-app expense_management
bench --site [your-site] install-app expense_management
```

2. The app will automatically create sample expense types

## Usage

### Creating Expense Types
1. Go to **Expense Management > Expense Type**
2. Create new expense types with appropriate default accounts
3. Set active status as needed

### Recording Expenses
1. Go to **Expense Management > Expense**
2. Fill in the expense details:
   - Select expense date and company
   - Choose expense type (auto-fills expense account)
   - Enter description and amount
   - Select payment account and mode
3. **Preview GL Entries** to review accounting impact
4. **Submit** to create GL entries

### Viewing Reports
1. Go to **Reports > Expense Summary**
2. Set filters as needed
3. View and export expense data

## Accounting Standards

This app follows proper accounting standards:

### Double Entry Bookkeeping
- Every expense creates two GL entries
- Debit to Expense Account (increases expense)
- Credit to Payment Account (decreases cash/bank)

### Account Types
- **Expense Accounts**: Must be of type "Expense Account" or "Cost of Goods Sold"
- **Payment Accounts**: Must be of type "Cash" or "Bank"

### GL Entry Structure
```
Dr. Expense Account     $XXX
    Cr. Cash/Bank Account     $XXX
```

## Technical Details

### DocTypes
- **Expense Type**: Master data for expense categories
- **Expense**: Main transaction document (submittable)

### Key Features
- GL Entry creation on submit/cancel
- Account validation and filtering
- Multi-company support
- Preview functionality
- Comprehensive reporting

### Permissions
- **System Manager**: Full access
- **Accounts Manager**: Full access
- **Accounts User**: Create, submit, view
- **Employee**: View only

## Dependencies
- Frappe Framework
- ERPNext (for accounting features)

## License
MIT License

## Support
For issues and support, please contact the technical team.

#### License

mit
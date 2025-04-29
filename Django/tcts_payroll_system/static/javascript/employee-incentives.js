// Employee Incentives Handler
// This script manages the add/deduct functionality for employee salaries

// Global variables to keep track of incentives
let employeeIncentives = {};

// Function to calculate salary
function calculateSalary(employeeId) {
  const employee = getEmployeeData(employeeId);
  const ratePerDay = parseFloat(employee.ratePerDay || 0);
  const totalAttendance = parseInt(employee.totalAttendance || 0);
  const baseSalary = ratePerDay * totalAttendance;
  
  // Get incentives for this employee (default to 0 if not set)
  const incentiveAmount = parseFloat(employeeIncentives[employeeId]?.amount || 0);
  const incentiveType = employeeIncentives[employeeId]?.type || 'add';
  
  // Calculate total salary based on incentive type
  let totalSalary = baseSalary;
  if (incentiveType === 'add') {
    totalSalary += incentiveAmount;
  } else if (incentiveType === 'subtract') {
    totalSalary -= incentiveAmount;
  }
  
  // Ensure salary doesn't go below zero
  totalSalary = Math.max(totalSalary, 0);
  
  return totalSalary;
}

// Function to display the incentive popup for a specific employee
function showIncentivePopup(employeeId) {
  const employee = getEmployeeData(employeeId);
  const popup = document.getElementById('incentive-popup');
  
  // Update popup title with employee name
  const popupTitle = popup.querySelector('h1');
  popupTitle.textContent = `Add/Deduct for ${employee.first_name} ${employee.last_name}`;
  
  // Set the current incentive type and amount if they exist
  const currentIncentive = employeeIncentives[employeeId] || { type: 'add', amount: '' };
  
  // Set the radio button for the incentive type
  document.getElementById(currentIncentive.type).checked = true;
  
  // Set the amount field
  document.getElementById('field').value = currentIncentive.amount || '';
  
  // Store the employee ID on the form for submission
  popup.dataset.employeeId = employeeId;
  
  // Show the popup
  popup.classList.remove('invisible', 'opacity-0');
  popup.classList.add('visible', 'opacity-100');
  
  // Add event listener to the form submission
  const form = popup.querySelector('form');
  form.onsubmit = function(event) {
    event.preventDefault();
    saveIncentives(employeeId);
  };
}

// Function to save incentives and update salary
function saveIncentives(employeeId) {
  // Get the selected incentive type
  const addRadio = document.getElementById('add');
  const incentiveType = addRadio.checked ? 'add' : 'subtract';
  
  // Get the incentive amount
  const incentiveAmount = parseFloat(document.getElementById('field').value) || 0;
  
  // Save incentives for this employee
  employeeIncentives[employeeId] = {
    type: incentiveType,
    amount: incentiveAmount
  };
  
  // Update salary display for this employee
  updateSalaryDisplay(employeeId);
  
  // Close the popup
  closeIncentivePopup();
  
  // Save incentives to localStorage for persistence (optional)
  saveIncentivesToStorage();
}

// Function to cancel editing incentives
function cancelEditIncentives() {
  closeIncentivePopup();
}

// Function to close the incentive popup
function closeIncentivePopup() {
  const popup = document.getElementById('incentive-popup');
  popup.classList.remove('visible', 'opacity-100');
  popup.classList.add('invisible', 'opacity-0');
  
  // Clear form data
  document.getElementById('field').value = '';
  document.getElementById('add').checked = false;
  document.getElementById('subtract').checked = false;
}

// Function to update salary display
function updateSalaryDisplay(employeeId) {
  const salaryElement = document.getElementById(`salary-${employeeId}`);
  if (salaryElement) {
    const totalSalary = calculateSalary(employeeId);
    salaryElement.textContent = formatCurrency(totalSalary);
    
    // If there are incentives, show indicator
    const incentiveIndicator = document.getElementById(`incentive-indicator-${employeeId}`);
    if (incentiveIndicator) {
      const hasIncentives = employeeIncentives[employeeId] && employeeIncentives[employeeId].amount > 0;
      incentiveIndicator.style.display = hasIncentives ? 'inline-block' : 'none';
    }
  }
}

// Function to update all salary displays when attendance changes
function updateAllSalaries() {
  // Get all employees
  const employees = getAllEmployees();
  
  // Update salary for each employee
  employees.forEach(employee => {
    updateSalaryDisplay(employee.id);
  });
}

// Helper function to format currency
function formatCurrency(amount) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'PHP', // Change to your currency
    minimumFractionDigits: 2
  }).format(amount);
}

// Function to save incentives to localStorage for persistence
function saveIncentivesToStorage() {
  localStorage.setItem('employeeIncentives', JSON.stringify(employeeIncentives));
}

// Function to load incentives from localStorage
function loadIncentivesFromStorage() {
  const savedIncentives = localStorage.getItem('employeeIncentives');
  if (savedIncentives) {
    employeeIncentives = JSON.parse(savedIncentives);
  }
}

// Mock function to get employee data - replace with your actual data fetching logic
function getEmployeeData(employeeId) {
  // This should be replaced with your actual logic to fetch employee data
  // For now, return mock data
  return {
    id: employeeId,
    first_name: 'John',
    last_name: 'Doe',
    ratePerDay: 500,
    totalAttendance: 22
  };
}

// Mock function to get all employees - replace with your actual logic
function getAllEmployees() {
  // This should be replaced with your actual logic to fetch all employees
  // For now, return mock data
  return [
    {
      id: 1,
      first_name: 'John',
      last_name: 'Doe',
      ratePerDay: 500,
      totalAttendance: 22
    }
  ];
}

// Initialize when the page loads
document.addEventListener('DOMContentLoaded', function() {
  // Load saved incentives
  loadIncentivesFromStorage();
  
  // Update all salary displays
  updateAllSalaries();
  
  // Add event listener to the confirm button
  const confirmButton = document.querySelector('#incentive-popup input[type="submit"]');
  confirmButton.addEventListener('click', function() {
    const employeeId = document.getElementById('incentive-popup').dataset.employeeId;
    saveIncentives(employeeId);
  });
  
  // Add hook for attendance changes - assuming there's an event or callback when attendance changes
  // This is a placeholder and needs to be integrated with your attendance update system
  window.addEventListener('attendanceUpdated', function(event) {
    // Update all salaries when attendance changes
    updateAllSalaries();
  });
});
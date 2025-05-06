// Get the canvas element
const donutCanvas = document.getElementById('donut');
const periodToggles = document.querySelectorAll('.period-toggle');

// Set up Chart.js donut chart
let attendanceChart = null;

// Global state 
let activePeriod = 'day'; // Default is daily view

// Colors for chart
const chartColors = {
  present: '#4CAF50', // Green for present
  absent: '#F44336'   // Red for absent
};

// Function to fetch attendance data from API
// In your attendance_chart.js
async function fetchAttendanceData(period) {
  try {
    // Update to use the Django URL
    const endpoint = `/attendance/summary/?period=${period}`;
    const response = await fetch(endpoint);
    
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error fetching attendance data:', error);
    // Return default data in case of error
    return {
      present: 0,
      absent: 0
    };
  }
}

// Function to update chart with new data
function updateChart(presentCount, absentCount) {
  // Destroy existing chart if it exists
  if (attendanceChart) {
    attendanceChart.destroy();
  }
  
  // Create new chart
  attendanceChart = new Chart(donutCanvas, {
    type: 'doughnut',
    data: {
      labels: ['Present', 'Absent'],
      datasets: [{
        data: [presentCount, absentCount],
        backgroundColor: [chartColors.present, chartColors.absent],
        borderWidth: 0,
        hoverOffset: 5
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      cutout: '70%',
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            font: {
              family: 'Roboto',
              size: 12
            },
            padding: 15
          }
        },
        tooltip: {
          callbacks: {
            label: function(context) {
              const label = context.label || '';
              const value = context.raw || 0;
              const total = context.dataset.data.reduce((acc, current) => acc + current, 0);
              const percentage = Math.round((value / total) * 100);
              return `${label}: ${value} (${percentage}%)`;
            }
          }
        }
      },
      // Center text plugin
      layout: {
        padding: 10
      }
    },
    plugins: [{
      id: 'centerText',
      beforeDraw: function(chart) {
        const width = chart.width;
        const height = chart.height;
        const ctx = chart.ctx;
        
        ctx.restore();
        
        // Total count
        const total = chart.data.datasets[0].data.reduce((sum, value) => sum + value, 0);
        
        // Font settings for total
        ctx.font = 'bold 20px Roboto';
        ctx.textBaseline = 'middle';
        ctx.textAlign = 'center';
        ctx.fillStyle = '#1E1E1E';
        
        // Draw total number
        ctx.fillText(total, width / 2, height / 2 - 10);
        
        // Font settings for "Total" label
        ctx.font = '12px Roboto';
        ctx.fillStyle = '#1E1E1ECC';
        
        // Draw "Total" label
        ctx.fillText('Total', width / 2, height / 2 + 10);
        
        ctx.save();
      }
    }]
  });
}

// Function to initialize dashboard with data
async function initializeAttendanceChart(period) {
  // Update active toggle button
  periodToggles.forEach(toggle => {
    if (toggle.dataset.period === period) {
      toggle.classList.remove('bg-[#E1E1E1]');
      toggle.classList.add('bg-[#F8D146]');
    } else {
      toggle.classList.remove('bg-[#F8D146]');
      toggle.classList.add('bg-[#E1E1E1]');
    }
  });
  
  // Fetch data for the selected period
  const data = await fetchAttendanceData(period);
  
  // Update chart with new data
  updateChart(data.present, data.absent);
}

// Add event listeners to period toggle buttons
periodToggles.forEach(toggle => {
  toggle.addEventListener('click', function() {
    const period = this.dataset.period;
    activePeriod = period;
    initializeAttendanceChart(period);
  });
});

// Initialize with default period (day)
document.addEventListener('DOMContentLoaded', function() {
  initializeAttendanceChart(activePeriod);
});

// Refresh data periodically (every 5 minutes)
setInterval(function() {
  initializeAttendanceChart(activePeriod);
}, 300000);
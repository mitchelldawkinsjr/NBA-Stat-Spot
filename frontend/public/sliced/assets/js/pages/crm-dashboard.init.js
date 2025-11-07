/*
-------------------------------------------------------------------------
* Template Name    : Sliced Pro - Tailwind CSS Admin & Dashboard Template   * 
* Author           : SRBThemes                                              *
* Version          : 1.0.0                                                  *
* Created          : October 2024                                           *
* File Description : apexchart init Js File                                 *
*------------------------------------------------------------------------
*/

//Customer Activities
var options = {
    series: [{
        name: 'Visit Customer',
        type: 'column',
        data: [34, 30, 16, 27, 11, 18, 28, 28, 50, 30, 18]
    }, {
        name: 'Add to Cart',
        type: 'area',
        data: [54, 64, 55, 40, 22, 35, 69, 46, 32, 30, 67]
    }, {
        name: 'Check Out',
        type: 'line',
        data: [38, 49, 53, 40, 29, 39, 56, 56, 59, 53, 60]
    }],
    chart: {
        height: 350,
        type: 'line',
        stacked: false,
        toolbar: {
            show: false,
        }
    },
    stroke: {
        width: [0, 2, 4],
        curve: 'smooth'
    },
    plotOptions: {
        bar: {
            columnWidth: '50%'
        }
    },
    colors: ["#0ea5e9", "#6366f1", "#eab308"],
    fill: {
        opacity: [1, 0.10, 1],
        gradient: {
            inverseColors: false,
            // shade: 'light',
            type: "vertical",
            opacityFrom: 0.85,
            opacityTo: 0,
            stops: [0, 100, 100, 100]
        }
    },
    labels: ['01/01/2003', '02/01/2003', '03/01/2003', '04/01/2003', '05/01/2003', '06/01/2003', '07/01/2003',
        '08/01/2003', '09/01/2003', '10/01/2003', '11/01/2003'
    ],
    markers: {
        size: 0
    },
    xaxis: {
        type: 'datetime'
    },
    tooltip: {
        shared: true,
        intersect: false,
    }
};

var chart = new ApexCharts(document.querySelector("#customerActivitiesChart"), options);
chart.render();


//sales charts
var options = {
    series: [44, 55, 41],
    chart: {
        height: 190,
        type: 'donut',
    },
    labels: ["ChatGTP", "Blogger", "Invision"],
    plotOptions: {
        pie: {
            startAngle: -90,
            endAngle: 270
        }
    },
    dataLabels: {
        enabled: false
    },
    fill: {
        type: 'gradient',
    },
    legend: {
        show: false
    },
};

var chart = new ApexCharts(document.querySelector("#salesChart"), options);
chart.render();
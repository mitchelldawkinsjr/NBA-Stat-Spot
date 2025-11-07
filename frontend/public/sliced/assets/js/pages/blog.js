/*
-------------------------------------------------------------------------
* Template Name    : Sliced Pro - Tailwind CSS Admin & Dashboard Template   * 
* Author           : SRBThemes                                              *
* Version          : 1.0.0                                                  *
* Created          : October 2024                                           *
* File Description : blog init Js File                                      *
*------------------------------------------------------------------------
*/

// Visiter
var options = {
    series: [{
        name: 'Servings',
        data: [44, 55, 41, 67, 22, 43, 21, 33, 45, 31, 87, 28, 46, 21, 65, 35]
    }],
    annotations: {
        points: [{
            seriesIndex: 0,
            label: {
                borderColor: '#775DD0',
                offsetY: 0,
                style: {
                    color: '#fff',
                    background: '#775DD0',
                },
            }
        }]
    },
    chart: {
        height: 280,
        type: 'bar',
        toolbar: 'fales',
    },
    plotOptions: {
        bar: {
            borderRadius: 10,
            columnWidth: '50%',
        }
    },
    dataLabels: {
        enabled: false
    },
    stroke: {
        width: 0
    },
    grid: {
        row: {
            colors: ['#fff', '#f2f2f2']
        }
    },
    xaxis: {
        labels: {
            rotate: -45
        },
        categories: ['2009', '2010', '2011', '2012', '2013', '2014', '2015', '2016', '2017',
            '2018', '2019', '2020', '2021', '2022', '2023', '2024'
        ],
        tickPlacement: 'on'
    },
    fill: {
        type: 'gradient',
        gradient: {
            shade: 'light',
            type: "horizontal",
            shadeIntensity: 0.25,
            gradientToColors: undefined,
            inverseColors: true,
            opacityFrom: 0.85,
            opacityTo: 0.85,
            stops: [50, 0, 100]
        },
    }
};

var chart = new ApexCharts(document.querySelector("#visiter"), options);
chart.render();

// pie
$(function () {
    var chart = $('#pie').highcharts({
        chart: {
            type: 'pie'
        },
        credits: {
            enabled: false
        },
        plotOptions: {
            pie: {
                innerSize: '98%',
                borderWidth: 16,
                borderColor: null,
                dataLabels: {
                    connectorWidth: 0
                }
            }
        },
        title: {
            verticalAlign: 'middle',
            floating: true,
            text: 'Visitors',
        },
        series: [{
            data: [
                ['26.%', 26.00],
                { visible: false, y: 5 },
                ['32.0%', 32.00],
                { visible: false, y: 5 },
                ['15.0%', 15.00],
                { visible: false, y: 5 },
                ['27.0%', 27.00],
                { visible: false, y: 5 },
            ],
            ignoreHiddenPoint: false
        }],
    });
});
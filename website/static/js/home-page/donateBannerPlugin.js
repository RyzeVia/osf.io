var m = require('mithril');
var $osf = require('js/osfHelpers');

// CSS
require('css/donate-banner.css');
require('css/meetings-and-conferences.css');

var currentDate = new Date();

var bannerOptions = [
    {
        startDate: new Date('August 7, 2017'),
        beforeLink: 'The Center for Open Science (COS) created the OSF and a suite of of free products to advance the ' +
            'work of the research community. If you value these tools, please make a gift to support COS’s efforts to ' +
            'improve and scale these services. ',
        linkText: 'Donate now!',
        afterLink: '',
        background:'.donate-banner.week-1'
    }, {
        startDate: new Date('August 14, 2017'),
        beforeLink: 'Thousands of researchers use the OSF and its related services daily. If you value the OSF, ',
        linkText: 'make a donation',
        afterLink: ' to support the Center for Open Science and its ongoing efforts to improve and advance these ' +
            'public goods.',
        background:'.donate-banner.week-2'

    }, {
        startDate: new Date('August 21, 2017'),
        beforeLink: 'The Center for Open Science (COS) created the OSF and its related services as public goods. While' +
            ' these services will always be free to use they are not free to build, improve and maintain. Please ',
        linkText: 'support the OSF and COS with a donation today.',
        afterLink: '',
        background:'.donate-banner.week-3'

    }, {
        startDate: new Date('August 28, 2017'),
        beforeLink: 'The Center for Open Science launched the OSF with the goal of creating a service where the entire' +
            ' research cycle is supported and barriers to accessing data are removed. ',
        linkText: 'Support COS’s efforts',
        afterLink: ' to advance the work of researchers with a gift today!',
        background:'.donate-banner.week-4'

    }, {
        startDate: new Date('September 4, 2017'),
        beforeLink: 'At the Center for Open Science (COS), we envision a future in which ideas, processes and ' +
            'outcomes of research are free and open to all. COS relies on contributions to build the free products you' +
            ' use and love. Help make the vision a reality with a ',
        linkText: 'gift today.',
        afterLink: '',
        background:'.donate-banner.week-5'
    }
];

function pickBanner(bannerOptions, date) {
    bannerOptions.sort(function (a,b){
        return a.startDate - b.startDate;
    });

    var i;
    for (i = 0; i < bannerOptions.length -1; i++) {
        if (bannerOptions[i].startDate <= date && bannerOptions[i + 1].startDate > date)
            return i;
    }
    return i;
}

bannerAttributes = bannerOptions[pickBanner(bannerOptions, currentDate)];

var Banner = {
    view: function(ctrl) {
        return m('.p-v-sm',
            m('.row',
                [
                    m('.col-md-12.m-v-sm',
                            m('div.conference-centering',
                                m('p', bannerAttributes.beforeLink,
                                    m('a.donate-text', { href:'https://cos.io/donate', onclick: function() {
                                        $osf.trackClick('link', 'click', 'DonateBanner - Donate now');
                                    }}, bannerAttributes.linkText), bannerAttributes.afterLink)
                            )
                    )
                ]
            )
        );
    }
};

var background = bannerAttributes.background;

module.exports = {
    Banner: Banner,
    background: background,
    pickBanner: pickBanner
};

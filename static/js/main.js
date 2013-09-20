YUI().use('intl','node-menunav', function(Y){
	Y.on('contentready', function(){
		this.plug(Y.Plugin.NodeMenuNav);  /*, { autoSubmenuDisplay: false, mouseOutHideDelay: 0 }*/
	}, '#blognav');

	prettyPrint();
});

function changePage(page) {
    window.location.search = '?page=' + page;
}
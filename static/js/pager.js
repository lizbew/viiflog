YUI().use('node', function(Y){
	
	Y.one('#pager-button').on('click', function(e) {
		var newpage = Y.one('#pager-select').get('value');
		window.location.search='?page='+newpage;
	});
});
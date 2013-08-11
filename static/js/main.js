YUI().use('intl','node-menunav', function(Y){
	var menu = Y.one('#blognav');

	menu.plug(Y.Plugin.NodeMenuNav);

	prettyPrint();
});
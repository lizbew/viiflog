(function(){
                var converter1 = Markdown.getSanitizingConverter();
                
                converter1.hooks.chain("preBlockGamut", function (text, rbg) {
                    return text.replace(/^ {0,3}""" *\n((?:.*?\n)+?) {0,3}""" *$/gm, function (whole, inner) {
                        return "<blockquote>" + rbg(inner) + "</blockquote>\n";
                    });
                });
                
                var editor1 = new Markdown.Editor(converter1);
                
                editor1.run();

})();

YUI().use('node', 'io-upload-iframe','json-parse',  function(Y){
  var cfg = {
    method: 'POST',
    form: {
      id: 'file-upload-form',
      upload: true
    }
  };
  function start(id, args){
    var id = id;
    var args = args.foo;
  }

  function complete(id, o, args) {
    var id = id;
    var data = o.responseText;
    var args = args[1];
    //console.log(data);
    var oj = Y.JSON.parse(data)
    var uri = Y.one('#file-upload-form').set('action',oj['upload_url']);
    Y.one('#uploaded-files').append('<li><a href="'+oj['download_url']+'">' + oj['file_name'] + '</a></li>');
  }

  function onFailure(id, resp, args) {
    alert(resp);
  }

  Y.on('io:start', start, Y, { 'foo':'bar'});
  Y.on('io:complete', complete, Y, ['fd', 'sf']);
  Y.on('io:failure', onFailure, Y, ['fd', 'sf']);

  Y.on('domready', function() {
    var uploadBtn = Y.one('#upload-file-button');
    if (uploadBtn) {
      uploadBtn.on('click', function(e) {
        e.preventDefault();
        
        var uri = Y.one('#file-upload-form').get('action');
        var request = Y.io(uri, cfg);
        return false;
      });
    }
  });
});

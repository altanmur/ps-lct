openerp.web_filedownload = function (instance) {

    instance.web_filedownload = instance.web_filedownload || {};

    var QWeb = instance.web.qweb,
        _t = instance.web._t;

    instance.web.client_actions.add("reload_dialog", "instance.web_filedownload.reload_dialog_after_button");
    instance.web_filedownload.reload_dialog_after_button = function (element, action) {
        var dialog = element.dialog_widget;
        if (dialog.active_view === 'form') {
            if (!!action.name) {
                dialog.__parentedParent.dialog_title = action.name;
                $('body').find(".ui-dialog-title").text(action.name);
            }
            dialog.views[dialog.active_view].controller.recursive_reload();
        }
    };

};

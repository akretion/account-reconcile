/** @odoo-module */

import {ListController} from "@web/views/list/list_controller";
import {listView} from "@web/views/list/list_view";
import {registry} from "@web/core/registry";

export class ReconcileMoveLineController extends ListController {
    async openRecord(record) {
        console.log(this.props.parentField, record.resId);
        var data = {};
        console.log(record);
        data[this.props.parentField] = [record.resId, record.display_name];
        this.props.parentRecord.update(data);
    }
}
ReconcileMoveLineController.props = {
    ...ListController.props,
    parentRecord: {type: Object, optional: true},
    parentField: {type: String, optional: true},
};
export const ReconcileMoveLineView = {
    ...listView,
    Controller: ReconcileMoveLineController,
};

registry.category("views").add("reconcile_move_line", ReconcileMoveLineView);

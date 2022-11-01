/** @odoo-module */
const {useState} = owl;
import {KanbanController} from "@web/views/kanban/kanban_controller";
import {View} from "@web/views/view";

export class ReconcileController extends KanbanController {
    async setup() {
        super.setup();
        this.state = useState({
            selectedRecordId: null,
        });
        this.model.addEventListener("update", () => this.selectRecord(), {once: true});
    }
    get viewReconcileInfo() {
        return {
            resId: this.state.selectedRecordId,
            type: "form",
            context: {
                ...(this.props.context || {}),
                form_view_ref: "account_reconcile_oca.bank_statement_line_form_view",
            },
            display: {controlPanel: false},
            mode: this.props.mode || "edit",
            resModel: this.props.resModel,
        };
    }
    async selectRecord(record) {
        var resId = undefined;
        if (record === undefined) {
            var records = this.model.root.records.filter(
                (modelRecord) =>
                    !modelRecord.data.is_reconciled || modelRecord.data.to_check
            );
            console.log(records);
            if (records.length === 0) {
                return;
            }
            resId = records[0].resId;
        } else {
            resId = record.resId;
        }
        if (!this.state.selectedRecordId || this.state.selectedRecordId !== resId) {
            this.state.selectedRecordId = resId;
        }
    }
    async openRecord(record) {
        this.selectRecord(record);
    }
}
ReconcileController.components = {
    ...ReconcileController.components,
    View,
};

ReconcileController.template = "account_reconcile_oca.ReconcileController";
ReconcileController.defaultProps = {};

/** @odoo-module **/

import {registry} from "@web/core/registry";

const {Component} = owl;

export class AccountReconcileDataWidget extends Component {
    getReconcileLines() {
        return this.props.record.data[this.props.name].data;
    }
    selectReconcileLine(ev, line) {
        this.props.record.update({
            manual_reference: line.reference,
            manual_account_id: line.account_id,
            manual_name: line.name,
            manual_amount: line.amount,
        });
    }
}
AccountReconcileDataWidget.template = "account_reconcile_oca.ReconcileDataWidget";

registry
    .category("fields")
    .add("account_reconcile_oca_data", AccountReconcileDataWidget);

/** @odoo-module **/

import fieldUtils from "web.field_utils";
import session from "web.session";
import {registry} from "@web/core/registry";

const {Component} = owl;

export class AccountReconcileDataWidget extends Component {
    getReconcileLines() {
        var data = this.props.record.data[this.props.name].data;
        for (var line in data) {
            data[line].amount_format = fieldUtils.format.monetary(
                data[line].amount,
                undefined,
                {
                    currency: session.get_currency(data[line].currency_id),
                }
            );
            data[line].debit_format = fieldUtils.format.monetary(
                data[line].debit,
                undefined,
                {
                    currency: session.get_currency(data[line].currency_id),
                }
            );
            data[line].credit_format = fieldUtils.format.monetary(
                data[line].credit,
                undefined,
                {
                    currency: session.get_currency(data[line].currency_id),
                }
            );
            data[line].date_format = fieldUtils.format.date(
                fieldUtils.parse.date(data[line].date, undefined, {isUTC: true})
            );
        }
        return data;
    }
    selectReconcileLine(ev, line) {
        this.props.record.update({
            manual_reference: line.reference,
            manual_account_id: line.account_id,
            manual_name: line.name,
            manual_amount: line.amount,
            manual_partner_id: line.partner_id,
        });
    }
}
AccountReconcileDataWidget.template = "account_reconcile_oca.ReconcileDataWidget";

registry
    .category("fields")
    .add("account_reconcile_oca_data", AccountReconcileDataWidget);

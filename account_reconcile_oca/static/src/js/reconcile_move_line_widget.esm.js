/** @odoo-module **/

import {Domain} from "@web/core/domain";
import {View} from "@web/views/view";
import {registry} from "@web/core/registry";

const {Component, useSubEnv} = owl;

export class AccountReconcileMatchWidget extends Component {
    setup() {
        // Necessary in order to avoid a loop
        useSubEnv({
            config: {},
        });
    }
    get listViewProperties() {
        return {
            type: "list",
            display: {
                controlPanel: {
                    // Hiding the control panel buttons
                    "top-left": false,
                    "bottom-left": false,
                },
            },
            resModel: this.props.record.fields[this.props.name].relation,
            searchMenuTypes: ["filter"],
            domain: new Domain(this.props.record.fields[this.props.name].domain).toList(
                this.props.record.evalContext
            ),
            context: {
                ...this.props.record.fields[this.props.name].context,
            },
            // Disables de selector
            allowSelectors: false,
            // We need to force the search view in order to show the right one,
            searchViewId: false,
            parentRecord: this.props.record,
            parentField: this.props.name,
        };
    }
}
AccountReconcileMatchWidget.template = "account_reconcile_oca.ReconcileMatchWidget";

AccountReconcileMatchWidget.components = {
    ...AccountReconcileMatchWidget.components,
    View,
};

registry
    .category("fields")
    .add("account_reconcile_oca_match", AccountReconcileMatchWidget);

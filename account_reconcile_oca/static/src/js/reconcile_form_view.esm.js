/** @odoo-module */

import {FormController} from "@web/views/form/form_controller";
import {formView} from "@web/views/form/form_view";
import {registry} from "@web/core/registry";
import {useViewButtons} from "@web/views/view_button/view_button_hook";
const {useRef} = owl;

export class ReconcileFormController extends FormController {
    setup() {
        super.setup(...arguments);
        const rootRef = useRef("root");
        useViewButtons(this.model, rootRef, {
            reload: this.reloadFormController.bind(this),
            beforeExecuteAction: this.beforeExecuteActionButton.bind(this),
            afterExecuteAction: this.afterExecuteActionButton.bind(this),
        });
    }
    async reloadFormController() {
        var is_reconciled = this.model.root.data.is_reconciled;
        await this.model.root.load();
        if (!is_reconciled && this.model.root.data.is_reconciled) {
            // This only happens when we press the reconcile button
            if (this.env.parentController) {
                // Refreshing
                await this.env.parentController.model.root.load();
                await this.env.parentController.render(true);
                this.env.parentController.selectRecord();
            }
        }
    }
}

export const ReconcileFormView = {
    ...formView,
    Controller: ReconcileFormController,
};

registry.category("views").add("reconcile_form", ReconcileFormView);

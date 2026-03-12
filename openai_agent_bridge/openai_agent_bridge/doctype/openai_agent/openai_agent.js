frappe.ui.form.on("OpenAI Agent", {
	refresh(frm) {
		apply_instruction_save_action(frm);
	},
	instructions(frm) {
		apply_instruction_save_action(frm);
	},
});

function apply_instruction_save_action(frm) {
	if (!should_show_instruction_save(frm)) {
		return;
	}

	frm.page.set_primary_action(__("Save Instructions"), () => save_instructions(frm));
}

function should_show_instruction_save(frm) {
	if (frm.is_new()) {
		return false;
	}

	if (frm.perm?.[0]?.write) {
		return false;
	}

	if (!frappe.user.has_role("OpenAI Agent User")) {
		return false;
	}

	const field = frm.get_field("instructions");
	return Boolean(field && !field.df.read_only);
}

async function save_instructions(frm) {
	const field = frm.get_field("instructions");
	const instructions = field?.value ?? frm.doc.instructions ?? "";

	await frappe.call({
		method: "openai_agent_bridge.api.update_agent_instructions",
		type: "POST",
		args: {
			agent_name: frm.doc.name,
			instructions,
		},
		freeze: true,
		freeze_message: __("Saving instructions"),
	});

	await frm.reload_doc();
	frappe.show_alert({ message: __("Instructions saved"), indicator: "green" });
}

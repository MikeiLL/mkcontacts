import {
    lindt,
    choc,
    replace_content,
    on,
    DOM,
} from "https://rosuav.github.io/choc/factory.js";
const {TABLE, TBODY, TD, TH, TR} = lindt; //autoimport
import {simpleconfirm} from "./utils.js";

export function render(state) {
    replace_content("main", [TABLE(TBODY(
        state.contacts.map((c, idx) => TR([TH(idx + ". " + c.fullname), TD(c.email), TD(c.phone)]))
    ))]);
}
console.log("loaded");
on("click", "button", async (e) => {
    const item_id = e.match.value;
    fetch("/updaterequest")
});

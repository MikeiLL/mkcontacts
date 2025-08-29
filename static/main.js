import {
    lindt,
    choc,
    replace_content,
    on,
    DOM,
} from "https://rosuav.github.io/choc/factory.js";
const {BUTTON, FORM, INPUT, LABEL, SPAN, TABLE, TBODY, TD, TH, TR} = lindt; //autoimport
import {simpleconfirm} from "./utils.js";

export function render(state) {
    replace_content("main", [
        FORM({id: "newcontact"}, (
        TABLE(TBODY([
            state.contacts.map((c, idx) => TR({'data-idx': idx}, [
                TH(idx + ". " + c.fullname), TD(c.email), TD(c.phone), TD(BUTTON({class: "delete",},"x"))
            ])),
            TR([
                TH([
                    LABEL([SPAN("fullname"), INPUT({type: "text", name: "fullname"})])
                ]), TD(
                    LABEL([SPAN("email"), INPUT({type: "text", name: "email"})])
                ), TD(
                    LABEL([SPAN("phone"), INPUT({type: "text", name: "phone"})])
                ), TD(
                    BUTTON({type: "submit"}, "new")
                )])
        ])))), // end form
    ]);
}
on("submit", "#newcontact", async (e) => {
    e.preventDefault();
    fetch("/newcontact", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            form: JSON.stringify(Object.fromEntries(new FormData(e.match)))
        }),
    })
});

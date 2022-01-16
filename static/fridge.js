window.setTimeout(function () {
    $(".alert").fadeTo(500, 0)
}, 4000);

$('.delete-ing').click(deleteIng)

async function deleteIng() {
    const id = $(this).parent().data('id')
    await axios.delete(`/fridge/ingredient/remove/${id}`)
    $(this).parent().remove()
}

$('#fridgeModalButton').click(showFridgeModal)

function showFridgeModal() {
    $('#fridgeModal').modal('show')
}

$('#fridgeModalCloseButton').click(hideFridgeModal)

function hideFridgeModal() {
    $('#fridgeModal').modal('hide')
    $('#ingResultsForm').empty()
}

$('#fridgeSearchButton').click(requestIngredients)

async function requestIngredients() {
    if ($('#ingResultsForm').children().length > 0) {
        $('#ingResultsForm').empty()
        // we don't need to worry about resetting the ings session list
        // because we're resetting it with our new request succeeding this step
    }
    const query = $('#query').val()
    const number = $('#quantity').val()
    let ings = await axios.get(`/ingredient/search/${query}&${number}`)

    for (let ingsData of ings.data) {
        let ing = $(generateIngResultHTML(ingsData));
        $('#ingResultsForm').append(ing)
    }
    $('#ingResultsForm').append(
        '<button id="ingAddButton" class="btn btn-success" type="button">add to fridge</button>'
    )
    $('#ingAddButton').click(addToFridge)
}


function generateIngResultHTML(ing) {
    return `<div><input type="radio" class="form-check-input" name="ingredient" id="${ing.id}" value="${ing.name}">
    <label class="form-check-label" for="${ing.id}">${ing.name}</label></div>`
}

async function addToFridge() {
    let ing_name = $(":radio:checked").val();
    let ing_id = $(":radio:checked").attr('id');

    // add ingredient to database
    await axios.post('/fridge/ingredient/add', json = { ing_name, ing_id });

    // Obtain ing id from fridge it's container within - we need this later
    // to delete from the database, using our current setup.
    let res_ing = await axios.get(`/fridge/ingredient/search/${ing_id}`);
    let ing_f_id = res_ing.data

    // generate the HTML and add to page
    let ing = $(generateNewFridgeItemHTML(ing_name, ing_f_id));
    $('#currentFridge').append(ing);
    $(`#dlt-btn-${ing_f_id}`).click(deleteIng)

    hideFridgeModal();
}

function generateNewFridgeItemHTML(ing_name, ing_id) {
    return `<li class="list-group-item d-flex justify-content-between align-items-center"
    data-id="${ing_id}">${ing_name}<button type="button" id="dlt-btn-${ing_id}" class="delete-ing btn btn-danger">X</button>
    </li>`
}

$("#rcpFridgeSearch").click(requestRcps);

async function requestRcps() {
    let res = await axios.get('/recipe/search')
    let rcps = res.data
    console.log(rcps)
}
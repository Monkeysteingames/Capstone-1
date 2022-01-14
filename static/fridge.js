$('.delete-ing').click(deleteIng)

async function deleteIng() {
    const id = $(this).parent().data('id')
    console.log(id)
    console.log(this)
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

}


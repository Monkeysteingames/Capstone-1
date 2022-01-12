$('.delete-ing').click(deleteIng)

async function deleteIng() {
    const id = $(this).parent().data('id')
    console.log(id)
    console.log(this)
    await axios.delete(`/fridge/ingredient/remove/${id}`)
    $(this).parent().remove()
}
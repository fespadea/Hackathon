from beaker import *
from pyteal import *


# This is the state class used to store the information needed to use this template
class glassState:
    # There are a max of 32 recovery addresses by default, but this can be increased by
    # just changing the 32 here to a larger number.
    glassAddresses = GlobalStateBlob(
        keys=32,
        descr="The addresses that will have the ability to work together to recover "
        "this smart contract in the case of a break glass emergency.",
    )

    numGlassAddresses = GlobalStateValue(
        stack_type=TealType.uint64,
        descr="The number of break glass addresses that this smart contract relies on "
        "in the case of a break glass emergency.",
    )

    glassOwners = GlobalStateBlob(
        keys=32,
        descr="This holds the addresses that each glass address believes should be the "
        "owner of this smart contract.",
    )

    owner = GlobalStateValue(
        stack_type=TealType.uint64,
        descr="The owner of this smart contract that holds the power",
    )


app = Application("HelloWorld", state=glassState)


# This creation function is used to initially set up the addresses that have the power
# to recover this smart contract.
@app.create(authorize=Authorize.only_creator())
def setGlassAddresses(glassAddresses: abi.Array) -> Expr:
    i = 0
    end = glassAddresses.length()
    # Here we assign the recovery addresses to what was passed to the function.
    # We also set their votes to the current owner.
    while i < end:
        app.state.glassAddresses.write(Int(i), Addr(str(glassAddresses[i])))
        app.state.glassOwners.write(Int(i), Global.creator_address())
        i += 1
    app.state.numGlassAddresses.set(end)
    return app.state.owner.set(Global.creator_address())


# This function is used by the owner to change the addresses that have the power
# to recover this smart contract.
@app.external(authorize=Authorize.only(app.state.owner))
def changeGlassAddresses(glassAddresses: abi.Array) -> Expr:
    i = 0
    end = glassAddresses.length()
    # Here we assign the recovery addresses to what was passed to the function.
    # We also set their votes to the current owner.
    while i < end:
        app.state.glassAddresses.write(Int(i), Addr(str(glassAddresses[i])))
        app.state.glassOwners.write(Int(i), Global.creator_address())
        i += 1
    app.state.numGlassAddresses.set(end)
    return app.state.glassAddresses.read(Int(i), end)


# This is the function that the recovery addresses can use to vote to change the
# address that acts as the owner of this smart contract. Once most of the recovery
# addresses have a majority vote for a specific address, that address will become
# the new owner of the smart contract.
@app.external
def claimNewOwner(newOwner: abi.Address) -> Expr:
    glassIndex = 0
    glassLimit = app.state.numGlassAddresses
    # Here we go through the recovery addresses to make sure that the sender is
    # actually one of them, and then we update their vote to the address they sent.
    while glassIndex < glassLimit:
        if (
            app.state.glassAddresses.read(Int(glassIndex), Int(glassIndex + 1))
            == Txn.sender()
        ):
            app.state.glassOwners.write(Int(glassIndex), Addr(str(newOwner)))
            break
        glassIndex += 1
    if glassIndex >= glassLimit:
        PermissionError
    votes = 0
    i = 0
    # Here we check to see if the address voted for by the sender now has the majority
    # of the votes, and then we update the owner to the new address if that is the case.
    while i < glassLimit:
        if app.state.glassOwners.read(Int(i), Int(i + 1)) == newOwner:
            votes += 1
        i += 1
    if votes > glassLimit / 2:
        app.state.owner.set(Addr(str(newOwner)))
    return app.state.owner


@app.delete(bare=True, authorize=Authorize.only(Global.creator_address()))
def delete() -> Expr:
    return Approve()


if __name__ == "__main__":
    app.build().export("./artifacts")

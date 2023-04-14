from beaker import *
from pyteal import *


class glassState:
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


@app.create(authorize=Authorize.only_creator())
def setGlassAddresses(glassAddresses: abi.Array) -> Expr:
    i = 0
    end = glassAddresses.length()
    while i < end:
        app.state.glassAddresses.write(Int(i), Addr(str(glassAddresses[i])))
        app.state.glassOwners.write(Int(i), Global.creator_address())
        i += 1
    app.state.numGlassAddresses.set(end)
    return app.state.owner.set(Global.creator_address())


@app.external(authorize=Authorize.only(app.state.owner))
def changeGlassAddresses(glassAddresses: abi.Array) -> Expr:
    i = 0
    end = glassAddresses.length()
    while i < end:
        app.state.glassAddresses.write(Int(i), Addr(str(glassAddresses[i])))
        app.state.glassOwners.write(Int(i), Global.creator_address())
        i += 1
    app.state.numGlassAddresses.set(end)
    return app.state.glassAddresses.read(Int(i), end)


@app.external
def claimNewOwner(newOwner: abi.Address) -> Expr:
    glassIndex = 0
    glassLimit = app.state.numGlassAddresses
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

from duty_bot.slack import format_message


def test_message_matches_prd_format():
    text = format_message(
        day="Sunday",
        date_text="July 5",
        rd="<@U123RD>",
        ard="<@U456ARD>",
        ram_a="<@U789RAMA>",
        ram_b="<@U999RAMB>",
    )
    assert text == (
        "Duty Rotation Sunday, July 5\n"
        "\n"
        "RD: <@U123RD>\n"
        "ARD: <@U456ARD>\n"
        "RAM A (phone/transport): <@U789RAMA>\n"
        "RAM B (rounds/backup): <@U999RAMB>"
    )

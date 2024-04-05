import { IApiResult } from '@/app/interfaces/IApiResult';
import { buildPathToDataFolder } from '@/server/DataLoader';
import { IApiDataEffect } from '@/server/gamedata/IApiDataEffect';
import { IApiEffect } from '@/server/gamedata/IApiEffect';
import { IApiEffectCard } from '@/server/gamedata/IApiEffectCard';
import { stringToEEffectType } from '@/server/gamedata/enums/EEffectType';
import { stringToEStat } from '@/server/gamedata/enums/EStat';
import { stringToETarget } from '@/server/gamedata/enums/ETarget';
import {promises as fsPromises} from 'fs';
import * as yaml from 'yaml';


export async function apiLogicLoadEffectData(category: string, artefactSetName: string) : Promise<IApiResult<IApiDataEffect>> {
    let subPath = artefactSetName.replaceAll("_", "/")
    const res : IApiResult<IApiDataEffect> = {success: false}
    const p = await buildPathToDataFolder("gamedata", category, subPath)
    if (p.status) {
        const a = yaml.parse((await fsPromises.readFile(p.path.concat(".yml"))).toString())
        const cards = []
        for (let i = 0; i < a["cards"].length; ++i) {
            const ca = a["cards"][i]
            const eff : IApiEffect[] = []
            const effPrecise : Record<number, IApiEffect[]> = {}
            if (ca["effects"] != undefined && Array.isArray(ca["effects"])) {
                for (let j = 0; j < ca["effects"].length; ++j) {
                    const ce = ca["effects"][j]
                    eff.push({
                        target: stringToETarget(ce["target"]),
                        stat: stringToEStat(ce["stat"]),
                        base: ce["base"],
                        maxvalue: ce["maxvalue"],
                        r1maxvalue: ce["r1maxvalue"],
                        r1ratio: ce["r1ratio"],
                        r1value: ce["r1value"],
                        r5maxvalue: ce["r5maxvalue"],
                        r5ratio: ce["r5ratio"],
                        r5value: ce["r5value"],
                        ratio: ce["ratio"],
                        source: ce["source"],
                        step: ce["step"],
                        value: ce["value"],
                    })
                }
            } else if (ca["effects"] != undefined && !Array.isArray(ca["effects"])) {
                console.log("we're here ! ")
                console.log(a)
                const keys = Object.keys(ca["effects"])
                console.log(keys)
                console.log(ca["effects"])
                for (let j = 0; j < keys.length; ++j) {
                    const cee = ca["effects"][keys[j]]
                    console.log(cee)
                    effPrecise[parseInt(keys[j])] = []
                    for (let jj = 0; jj < cee.length; ++jj) {
                        const ce = cee[jj]
                        effPrecise[parseInt(keys[j])].push({
                            target: stringToETarget(ce["target"]),
                            stat: stringToEStat(ce["stat"]),
                            base: ce["base"],
                            maxvalue: ce["maxvalue"],
                            r1maxvalue: ce["r1maxvalue"],
                            r1ratio: ce["r1ratio"],
                            r1value: ce["r1value"],
                            r5maxvalue: ce["r5maxvalue"],
                            r5ratio: ce["r5ratio"],
                            r5value: ce["r5value"],
                            ratio: ce["ratio"],
                            source: ce["source"],
                            step: ce["step"],
                            value: ce["value"],
                        })
                    }
                }
            }

            const c : IApiEffectCard = {
                name: ca["name"] == undefined ? a["name"].concat(" (default)") : ca["name"],
                type: stringToEEffectType(ca["type"]),
                keywords: ca["keywords"],
                maxstack: ca["maxstack"],
                tag: ca["tag"],
                text: ca["text"],
                source: ca["source"],
                effects: eff,
                effectsPrecise: effPrecise
            }

            cards.push(c)
        }

        const item : IApiDataEffect = {
            name: a["name"],
            cards: cards
        }

        res.content = item
        res.success = true
    }

    return res
}

export async function GET(request: Request, {params}: {params: {category: string, name: string}}) {
    const name = params.name
    const category = params.category
    let content : any = {message: "Data folder not found."}
    if (name != undefined && category != undefined) {
        const effect = await apiLogicLoadEffectData(category, name)
        content = effect
    }

    return Response.json(content, {headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        }
    })
}
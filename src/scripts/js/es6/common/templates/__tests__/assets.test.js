import { Assets } from '../assets'
import {} from ''

jest.useFakeTimers();

describe('Assets', () => {
    describe('create$listItem', () => {
        let nodeDoc;
        let spyGet;
        beforeEach(()=>{
            nodeDoc = {
                _id: 'my-asset-id',
                name: 'My Asset',
                pretty_created: '2 hours ago',
                node_type: 'asset',
                project: {
                    name: 'My Project',
                    url: 'url-to-project'
                },
                properties: {
                    content_type: 'image'
                }
            };

            spyGet = spyOn($, 'get').and.callFake(function(url) {
                let ajaxMock = $.Deferred();
                let response = {
                    variations: [{
                        size: 'l',
                        link: 'wrong-img-link',
                        width: 150,
                        height: 170,
                    },{
                        size: 'm',
                        link: 'img-link',
                        width: 50,
                        height: 70,
                    },{
                        size: 's',
                        link: 'wrong-img-link',
                        width: 5,
                        height: 7,
                    }]
                }
                ajaxMock.resolve(response);
                return ajaxMock.promise();
            });
        });
        describe('image content', () => {
            test('node with picture', done => {
                nodeDoc.picture = 'picture_id';
                let $card = Assets.create$listItem(nodeDoc);
                jest.runAllTimers();
                expect($card.length).toEqual(1);
                expect($card.prop('tagName')).toEqual('A');
                expect($card.hasClass('card asset')).toBeTruthy();
                expect($card.attr('href')).toEqual('/nodes/my-asset-id/redir');
                expect($card.attr('title')).toEqual('My Asset');
    
                let $body = $card.find('.card-body');
                expect($body.length).toEqual(1);
    
                let $title = $body.find('.card-title');
                expect($title.length).toEqual(1);
                
                expect(spyGet).toHaveBeenCalledTimes(1);
                expect(spyGet).toHaveBeenLastCalledWith('/api/files/picture_id');

                let $image = $card.find('img');
                expect($image.length).toEqual(1);

                let $imageSubsititure = $card.find('.pi-asset');
                expect($imageSubsititure.length).toEqual(0);
    
                let $progress = $card.find('.progress');
                expect($progress.length).toEqual(0);

                let $watched = $card.find('.card-label');
                expect($watched.length).toEqual(0);
                done();
            });

            test('node without picture', done => {
                let $card = Assets.create$listItem(nodeDoc);
                expect($card.length).toEqual(1);
                expect($card.prop('tagName')).toEqual('A');
                expect($card.hasClass('card asset')).toBeTruthy();
                expect($card.attr('href')).toEqual('/nodes/my-asset-id/redir');
                expect($card.attr('title')).toEqual('My Asset');
    
                let $body = $card.find('.card-body');
                expect($body.length).toEqual(1);
    
                let $title = $body.find('.card-title');
                expect($title.length).toEqual(1);

                expect(spyGet).toHaveBeenCalledTimes(0);

                let $image = $card.find('img');
                expect($image.length).toEqual(0);

                let $imageSubsititure = $card.find('.pi-asset');
                expect($imageSubsititure.length).toEqual(1);
    
                let $progress = $card.find('.progress');
                expect($progress.length).toEqual(0);

                let $watched = $card.find('.card-label');
                expect($watched.length).toEqual(0);
                done();
            });
        });
    })
});

